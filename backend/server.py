from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone
import pandas as pd
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from instagrapi import Client as InstaClient
from emergentintegrations.llm.chat import LlmChat, UserMessage
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Instagram client (lazy loading)
insta_client = None

# Models
class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    total_contacts: int = 0
    sent_count: int = 0

class Contact(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category_id: str
    username: str  # username for Instagram or email
    platform: str  # "instagram" or "email"
    status: str = "pending"  # pending, sent, failed
    sent_at: Optional[str] = None
    last_message: Optional[str] = None
    classification: Optional[str] = None  # positive, negative, neutral
    interest_score: Optional[int] = None

class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    contact_id: str
    content: str
    direction: str  # "outbound" or "inbound"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    classification: Optional[str] = None
    interest_score: Optional[int] = None

class ExcelImportResponse(BaseModel):
    categories: List[Dict]
    total_contacts: int

class SendMessageRequest(BaseModel):
    contact_ids: List[str]
    platform: str
    subject: Optional[str] = None
    message: str
    instagram_username: Optional[str] = None
    instagram_password: Optional[str] = None

class AnalyzeRequest(BaseModel):
    contact_id: str
    message: str

class SendChatMessageRequest(BaseModel):
    contact_id: str
    message: str

# Routes
@api_router.post("/excel/import", response_model=ExcelImportResponse)
async def import_excel(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Expected format: Category | Username/Email | Platform
        if not all(col in df.columns for col in ['Category', 'Username', 'Platform']):
            raise HTTPException(400, "Excel must have columns: Category, Username, Platform")
        
        categories_map = {}
        total_contacts = 0
        
        for _, row in df.iterrows():
            category_name = str(row['Category']).strip()
            username = str(row['Username']).strip()
            platform = str(row['Platform']).strip().lower()
            
            if platform not in ['instagram', 'email']:
                continue
            
            # Create or get category
            if category_name not in categories_map:
                cat_id = str(uuid.uuid4())
                categories_map[category_name] = {
                    'id': cat_id,
                    'name': category_name,
                    'total_contacts': 0,
                    'sent_count': 0
                }
            
            # Create contact
            contact = Contact(
                category_id=categories_map[category_name]['id'],
                username=username,
                platform=platform
            )
            await db.contacts.insert_one(contact.model_dump())
            categories_map[category_name]['total_contacts'] += 1
            total_contacts += 1
        
        # Insert categories
        for cat_data in categories_map.values():
            await db.categories.insert_one(cat_data)
        
        # Clean categories data to avoid ObjectId serialization issues
        clean_categories = []
        for cat_data in categories_map.values():
            clean_categories.append({
                'id': cat_data['id'],
                'name': cat_data['name'],
                'total_contacts': cat_data['total_contacts'],
                'sent_count': cat_data['sent_count']
            })
        
        return ExcelImportResponse(
            categories=clean_categories,
            total_contacts=total_contacts
        )
    except Exception as e:
        raise HTTPException(500, f"Import failed: {str(e)}")

@api_router.get("/categories")
async def get_categories():
    categories = await db.categories.find({}, {"_id": 0}).to_list(1000)
    for cat in categories:
        contacts = await db.contacts.find({"category_id": cat['id']}, {"_id": 0}).to_list(1000)
        cat['contacts'] = contacts
        cat['sent_count'] = sum(1 for c in contacts if c['status'] == 'sent')
    return categories

@api_router.post("/messages/send")
async def send_messages(req: SendMessageRequest):
    results = []
    
    for contact_id in req.contact_ids:
        contact = await db.contacts.find_one({"id": contact_id}, {"_id": 0})
        if not contact:
            results.append({"contact_id": contact_id, "status": "error", "message": "Contact not found"})
            continue
        
        try:
            if req.platform == "email":
                await send_email(contact['username'], req.subject or "Message", req.message)
            elif req.platform == "instagram":
                await send_instagram_dm(contact['username'], req.message, req.instagram_username, req.instagram_password)
            
            # Update contact
            await db.contacts.update_one(
                {"id": contact_id},
                {"$set": {
                    "status": "sent",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "last_message": req.message
                }}
            )
            
            # Save message
            message = Message(
                contact_id=contact_id,
                content=req.message,
                direction="outbound"
            )
            await db.messages.insert_one(message.model_dump())
            
            results.append({"contact_id": contact_id, "status": "success"})
        except Exception as e:
            await db.contacts.update_one({"id": contact_id}, {"$set": {"status": "failed"}})
            results.append({"contact_id": contact_id, "status": "error", "message": str(e)})
    
    return {"results": results}

async def send_email(to_email: str, subject: str, body: str):
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_email = os.environ.get('SMTP_EMAIL')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    
    if not smtp_email or not smtp_password:
        raise Exception("SMTP credentials not configured")
    
    msg = MIMEMultipart()
    msg['From'] = smtp_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send_email_sync, smtp_host, smtp_port, smtp_email, smtp_password, msg)

def _send_email_sync(host, port, email, password, msg):
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(email, password)
        server.send_message(msg)

async def send_instagram_dm(username: str, message: str, insta_user: str, insta_pass: str):
    global insta_client
    
    if not insta_user or not insta_pass:
        raise Exception("Instagram credentials required")
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send_instagram_dm_sync, username, message, insta_user, insta_pass)

def _send_instagram_dm_sync(username: str, message: str, insta_user: str, insta_pass: str):
    cl = InstaClient()
    cl.login(insta_user, insta_pass)
    user_id = cl.user_id_from_username(username)
    cl.direct_send(message, [user_id])

@api_router.post("/messages/analyze")
async def analyze_message(req: AnalyzeRequest):
    try:
        # Use OpenAI GPT-4o via emergentintegrations
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        chat = LlmChat(
            api_key=api_key,
            session_id=f"analyze-{req.contact_id}",
            system_message="You are a sentiment analyzer. Classify the message as Positive, Negative, or Neutral and provide an interest score from 0-100. Reply in JSON format: {\"classification\": \"Positive/Negative/Neutral\", \"score\": 0-100, \"reason\": \"brief explanation\"}"
        ).with_model("openai", "gpt-4o")
        
        user_message = UserMessage(text=f"Analyze this message: {req.message}")
        response = await chat.send_message(user_message)
        
        # Parse response
        import json
        result = json.loads(response)
        
        classification = result['classification'].lower()
        score = result['score']
        
        # Update contact
        await db.contacts.update_one(
            {"id": req.contact_id},
            {"$set": {
                "classification": classification,
                "interest_score": score,
                "last_message": req.message
            }}
        )
        
        # Save message
        message = Message(
            contact_id=req.contact_id,
            content=req.message,
            direction="inbound",
            classification=classification,
            interest_score=score
        )
        await db.messages.insert_one(message.model_dump())
        
        return {"classification": classification, "score": score, "reason": result.get('reason', '')}
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")

@api_router.get("/conversations")
async def get_conversations():
    contacts = await db.contacts.find(
        {"classification": {"$in": ["positive", "neutral"]}},
        {"_id": 0}
    ).to_list(1000)
    return contacts

@api_router.get("/conversations/{contact_id}")
async def get_conversation(contact_id: str):
    contact = await db.contacts.find_one({"id": contact_id}, {"_id": 0})
    if not contact:
        raise HTTPException(404, "Contact not found")
    
    messages = await db.messages.find(
        {"contact_id": contact_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(1000)
    
    return {"contact": contact, "messages": messages}

@api_router.post("/conversations/{contact_id}/message")
async def send_chat_message(contact_id: str, req: SendChatMessageRequest):
    contact = await db.contacts.find_one({"id": contact_id}, {"_id": 0})
    if not contact:
        raise HTTPException(404, "Contact not found")
    
    # Save message
    message = Message(
        contact_id=contact_id,
        content=req.message,
        direction="outbound"
    )
    await db.messages.insert_one(message.model_dump())
    
    return {"success": True, "message": message.model_dump()}

@api_router.get("/analytics")
async def get_analytics():
    total_contacts = await db.contacts.count_documents({})
    sent_count = await db.contacts.count_documents({"status": "sent"})
    
    positive_count = await db.contacts.count_documents({"classification": "positive"})
    negative_count = await db.contacts.count_documents({"classification": "negative"})
    neutral_count = await db.contacts.count_documents({"classification": "neutral"})
    
    categories = await db.categories.find({}, {"_id": 0}).to_list(100)
    
    return {
        "total_contacts": total_contacts,
        "sent_count": sent_count,
        "pending_count": total_contacts - sent_count,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "categories": categories
    }

class ResetStatusRequest(BaseModel):
    scope: str  # "all", "category", "selected"
    category_id: Optional[str] = None
    contact_ids: Optional[List[str]] = None

@api_router.post("/contacts/reset-status")
async def reset_contact_status(req: ResetStatusRequest):
    try:
        reset_count = 0
        
        if req.scope == "all":
            # Reset all contacts
            result = await db.contacts.update_many(
                {},
                {"$set": {
                    "status": "pending",
                    "sent_at": None,
                    "last_message": None,
                    "classification": None,
                    "interest_score": None
                }}
            )
            reset_count = result.modified_count
            
            # Update all category counters
            await db.categories.update_many(
                {},
                {"$set": {"sent_count": 0}}
            )
            
        elif req.scope == "category" and req.category_id:
            # Reset contacts in specific category
            result = await db.contacts.update_many(
                {"category_id": req.category_id},
                {"$set": {
                    "status": "pending",
                    "sent_at": None,
                    "last_message": None,
                    "classification": None,
                    "interest_score": None
                }}
            )
            reset_count = result.modified_count
            
            # Update category counter
            await db.categories.update_one(
                {"id": req.category_id},
                {"$set": {"sent_count": 0}}
            )
            
        elif req.scope == "selected" and req.contact_ids:
            # Reset selected contacts
            result = await db.contacts.update_many(
                {"id": {"$in": req.contact_ids}},
                {"$set": {
                    "status": "pending",
                    "sent_at": None,
                    "last_message": None,
                    "classification": None,
                    "interest_score": None
                }}
            )
            reset_count = result.modified_count
            
            # Update category counters for affected categories
            affected_contacts = await db.contacts.find(
                {"id": {"$in": req.contact_ids}},
                {"_id": 0, "category_id": 1}
            ).to_list(1000)
            
            category_ids = list(set([c["category_id"] for c in affected_contacts]))
            for cat_id in category_ids:
                sent_count = await db.contacts.count_documents({
                    "category_id": cat_id,
                    "status": "sent"
                })
                await db.categories.update_one(
                    {"id": cat_id},
                    {"$set": {"sent_count": sent_count}}
                )
        
        return {
            "success": True,
            "reset_count": reset_count,
            "message": f"Reset {reset_count} contact(s) successfully"
        }
    except Exception as e:
        raise HTTPException(500, f"Reset failed: {str(e)}")

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()