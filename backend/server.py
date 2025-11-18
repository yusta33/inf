from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import time
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, validator
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone
import pandas as pd
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from instagrapi import Client as InstaClient
import asyncio
from collections import deque
import random

# Import authentication module
from auth.router import create_auth_router
from auth.dependencies import get_current_user_dependency
from auth.security import validate_auth_config
from auth.models import User

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Environment variable validation
def get_required_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        logger.error(f"Required environment variable {key} is not set")
        raise ValueError(f"Required environment variable {key} is not set")
    return value

# MongoDB connection
try:
    mongo_url = get_required_env('MONGO_URL')
    db_name = get_required_env('DB_NAME')
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    logger.info("MongoDB connection initialized")
except Exception as e:
    logger.critical(f"Failed to initialize MongoDB: {str(e)}")
    raise

# Create the main app
app = FastAPI(title="InboxHub CRM API", version="2.0.0")
api_router = APIRouter(prefix="/api")

# Create auth dependency for protecting routes
get_current_user = get_current_user_dependency(db)

# Constants
RESET_FIELDS = {
    "status": "pending",
    "sent_at": None,
    "last_message": None,
    "classification": None,
    "interest_score": None
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_CONTACTS_PER_REQUEST = 100

# In-memory message queue
message_queue = deque(maxlen=1000)
processing_queue = False

# ============================================================================
# MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and responses with timing"""
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]

    logger.info(f"[{request_id}] {request.method} {request.url.path} - Request started")

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Time: {process_time:.3f}s"
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Error: {str(e)} - Time: {process_time:.3f}s"
        )
        raise

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if app.debug else "An unexpected error occurred",
            "path": request.url.path
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP exception handler"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "path": request.url.path}
    )

# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def sanitize_string(value: str, max_length: int = 100, field_name: str = "value") -> str:
    """Sanitize and validate string input"""
    if not value or pd.isna(value) or str(value).strip() in ['', 'nan', 'None']:
        raise ValueError(f"{field_name} cannot be empty")

    sanitized = str(value).strip()

    if len(sanitized) > max_length:
        raise ValueError(f"{field_name} exceeds {max_length} characters")

    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", ';', '\\', '`']
    if any(char in sanitized for char in dangerous_chars):
        logger.warning(f"Dangerous characters detected in {field_name}: {sanitized}")
        sanitized = ''.join(char for char in sanitized if char not in dangerous_chars)

    return sanitized

def validate_uuid(uuid_string: str) -> bool:
    """Validate UUID format"""
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, AttributeError):
        return False

def validate_email(email: str) -> bool:
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    total_contacts: int = 0
    sent_count: int = 0

    @validator('name')
    def validate_name(cls, v):
        return sanitize_string(v, max_length=100, field_name="Category name")

class Contact(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category_id: str
    username: str
    platform: str
    status: str = "pending"
    sent_at: Optional[str] = None
    last_message: Optional[str] = None
    classification: Optional[str] = None
    interest_score: Optional[int] = None

    @validator('username')
    def validate_username(cls, v):
        return sanitize_string(v, max_length=200, field_name="Username")

    @validator('platform')
    def validate_platform(cls, v):
        if v not in ['instagram', 'email']:
            raise ValueError("Platform must be 'instagram' or 'email'")
        return v

class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    contact_id: str
    content: str
    direction: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    classification: Optional[str] = None
    interest_score: Optional[int] = None

    @validator('direction')
    def validate_direction(cls, v):
        if v not in ['inbound', 'outbound']:
            raise ValueError("Direction must be 'inbound' or 'outbound'")
        return v

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

    @validator('contact_ids')
    def validate_contact_ids(cls, v):
        if len(v) > MAX_CONTACTS_PER_REQUEST:
            raise ValueError(f"Cannot send to more than {MAX_CONTACTS_PER_REQUEST} contacts at once")
        for contact_id in v:
            if not validate_uuid(contact_id):
                raise ValueError(f"Invalid contact ID format: {contact_id}")
        return v

    @validator('platform')
    def validate_platform(cls, v):
        if v not in ['instagram', 'email']:
            raise ValueError("Platform must be 'instagram' or 'email'")
        return v

    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        if len(v) > 5000:
            raise ValueError("Message exceeds 5000 characters")
        return v.strip()

class AnalyzeRequest(BaseModel):
    contact_id: str
    message: str

    @validator('contact_id')
    def validate_contact_id(cls, v):
        if not validate_uuid(v):
            raise ValueError("Invalid contact ID format")
        return v

class SendChatMessageRequest(BaseModel):
    contact_id: str
    message: str

class ResetStatusRequest(BaseModel):
    scope: str
    category_id: Optional[str] = None
    contact_ids: Optional[List[str]] = None

    @validator('scope')
    def validate_scope(cls, v):
        if v not in ['all', 'category', 'selected']:
            raise ValueError("Scope must be 'all', 'category', or 'selected'")
        return v

# ============================================================================
# EXCEL IMPORT FUNCTIONS
# ============================================================================

async def parse_excel_file(contents: bytes) -> pd.DataFrame:
    """Parse and validate Excel file"""
    logger.info(f"Parsing Excel file ({len(contents)} bytes)")

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")

    try:
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        logger.error(f"Failed to parse Excel file: {str(e)}")
        raise HTTPException(400, f"Invalid Excel file: {str(e)}")

    if df.empty:
        raise HTTPException(400, "Excel file is empty")

    required_columns = ['Category', 'Username', 'Platform']
    if not all(col in df.columns for col in required_columns):
        raise HTTPException(
            400,
            f"Excel must have columns: {', '.join(required_columns)}. Found: {', '.join(df.columns)}"
        )

    logger.info(f"Successfully parsed Excel with {len(df)} rows")
    return df

async def process_excel_data(df: pd.DataFrame) -> tuple:
    """Process and validate Excel data"""
    categories_map = {}
    total_contacts = 0
    errors = []

    for index, row in df.iterrows():
        try:
            # Validate and sanitize inputs
            category_name = sanitize_string(row['Category'], field_name="Category")
            username = sanitize_string(row['Username'], field_name="Username")
            platform = str(row['Platform']).strip().lower()

            if platform not in ['instagram', 'email']:
                errors.append(f"Row {index + 2}: Invalid platform '{platform}'")
                continue

            # Validate email format if platform is email
            if platform == 'email' and not validate_email(username):
                errors.append(f"Row {index + 2}: Invalid email format '{username}'")
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

        except ValueError as e:
            errors.append(f"Row {index + 2}: {str(e)}")
            continue
        except Exception as e:
            logger.error(f"Error processing row {index + 2}: {str(e)}")
            errors.append(f"Row {index + 2}: Unexpected error")
            continue

    if total_contacts == 0:
        raise HTTPException(400, f"No valid contacts found. Errors: {'; '.join(errors[:5])}")

    if errors:
        logger.warning(f"Excel import completed with {len(errors)} errors: {errors[:5]}")

    return categories_map, total_contacts, errors

# ============================================================================
# SENTIMENT ANALYSIS (NO-OP REPLACEMENT)
# ============================================================================

def analyze_sentiment_simple(message: str) -> Dict:
    """
    Simple sentiment analyzer (replaces LLM integration).
    Returns a static or simple rule-based classification.
    """
    message_lower = message.lower()

    # Simple keyword-based classification
    positive_keywords = ['great', 'good', 'excellent', 'love', 'amazing', 'awesome', 'interested', 'yes', 'perfect', 'thanks']
    negative_keywords = ['bad', 'terrible', 'awful', 'hate', 'no', 'not interested', 'stop', 'unsubscribe']

    positive_count = sum(1 for word in positive_keywords if word in message_lower)
    negative_count = sum(1 for word in negative_keywords if word in message_lower)

    if positive_count > negative_count:
        classification = "positive"
        score = min(60 + (positive_count * 10), 95)
        reason = "Message contains positive keywords"
    elif negative_count > positive_count:
        classification = "negative"
        score = max(40 - (negative_count * 10), 5)
        reason = "Message contains negative keywords"
    else:
        classification = "neutral"
        score = random.randint(40, 60)
        reason = "Message appears neutral"

    return {
        "classification": classification,
        "score": score,
        "reason": reason
    }

# ============================================================================
# ROUTES
# ============================================================================

@api_router.post("/excel/import", response_model=ExcelImportResponse)
async def import_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Import contacts from Excel file with validation (requires authentication)"""
    logger.info(f"Starting Excel import: {file.filename} by user {current_user.email}")

    try:
        # Parse file
        contents = await file.read()
        df = await parse_excel_file(contents)

        # Process data
        categories_map, total_contacts, errors = await process_excel_data(df)

        # Insert categories
        for cat_data in categories_map.values():
            await db.categories.insert_one(cat_data)

        # Prepare response
        clean_categories = [
            {
                'id': cat['id'],
                'name': cat['name'],
                'total_contacts': cat['total_contacts'],
                'sent_count': cat['sent_count']
            }
            for cat in categories_map.values()
        ]

        logger.info(f"Excel import completed: {total_contacts} contacts, {len(errors)} errors")

        return ExcelImportResponse(
            categories=clean_categories,
            total_contacts=total_contacts
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Excel import failed: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Import failed: {str(e)}")

@api_router.get("/categories")
async def get_categories():
    """Get all categories with contacts"""
    logger.info("Fetching categories")
    try:
        categories = await db.categories.find({}, {"_id": 0}).to_list(1000)
        for cat in categories:
            contacts = await db.contacts.find({"category_id": cat['id']}, {"_id": 0}).to_list(1000)
            cat['contacts'] = contacts
            cat['sent_count'] = sum(1 for c in contacts if c['status'] == 'sent')
        logger.info(f"Retrieved {len(categories)} categories")
        return categories
    except Exception as e:
        logger.error(f"Failed to fetch categories: {str(e)}")
        raise HTTPException(500, "Failed to fetch categories")

@api_router.post("/messages/send")
async def send_messages(
    req: SendMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """Send messages to contacts (adds to queue, requires authentication)"""
    logger.info(f"Queuing messages for {len(req.contact_ids)} contacts by user {current_user.email}")

    results = []

    for contact_id in req.contact_ids:
        contact = await db.contacts.find_one({"id": contact_id}, {"_id": 0})
        if not contact:
            results.append({"contact_id": contact_id, "status": "error", "message": "Contact not found"})
            continue

        # Add to message queue
        message_queue.append({
            "contact_id": contact_id,
            "contact": contact,
            "platform": req.platform,
            "subject": req.subject,
            "message": req.message,
            "instagram_username": req.instagram_username,
            "instagram_password": req.instagram_password,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        results.append({"contact_id": contact_id, "status": "queued"})

    # Start processing if not already running
    if not processing_queue:
        asyncio.create_task(process_message_queue())

    logger.info(f"Queued {len(results)} messages")
    return {"results": results, "queue_size": len(message_queue)}

async def process_message_queue():
    """Process messages from the queue"""
    global processing_queue
    processing_queue = True

    logger.info("Started processing message queue")

    while message_queue:
        item = message_queue.popleft()

        try:
            contact_id = item["contact_id"]
            contact = item["contact"]
            platform = item["platform"]
            message = item["message"]

            logger.info(f"Processing message for contact {contact_id} via {platform}")

            if platform == "email":
                await send_email(contact['username'], item["subject"] or "Message", message)
            elif platform == "instagram":
                await send_instagram_dm(
                    contact['username'],
                    message,
                    item["instagram_username"],
                    item["instagram_password"]
                )

            # Update contact
            await db.contacts.update_one(
                {"id": contact_id},
                {"$set": {
                    "status": "sent",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "last_message": message
                }}
            )

            # Save message
            msg = Message(
                contact_id=contact_id,
                content=message,
                direction="outbound"
            )
            await db.messages.insert_one(msg.model_dump())

            logger.info(f"Successfully sent message to {contact_id}")

        except Exception as e:
            logger.error(f"Failed to send message to {item['contact_id']}: {str(e)}")
            await db.contacts.update_one({"id": item["contact_id"]}, {"$set": {"status": "failed"}})

        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)

    processing_queue = False
    logger.info("Finished processing message queue")

async def send_email(to_email: str, subject: str, body: str):
    """Send email with validation"""
    if not validate_email(to_email):
        raise Exception(f"Invalid email address: {to_email}")

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
    logger.info(f"Email sent to {to_email}")

def _send_email_sync(host, port, email, password, msg):
    """Synchronous email sending"""
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(email, password)
        server.send_message(msg)

async def send_instagram_dm(username: str, message: str, insta_user: str, insta_pass: str):
    """Send Instagram DM with error handling"""
    if not insta_user or not insta_pass:
        raise Exception("Instagram credentials required")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send_instagram_dm_sync, username, message, insta_user, insta_pass)
    logger.info(f"Instagram DM sent to @{username}")

def _send_instagram_dm_sync(username: str, message: str, insta_user: str, insta_pass: str):
    """Synchronous Instagram DM sending with comprehensive error handling"""
    try:
        cl = InstaClient()
        cl.login(insta_user, insta_pass)
        user_id = cl.user_id_from_username(username)
        cl.direct_send(message, [user_id])
    except Exception as e:
        logger.error(f"Instagram DM failed for @{username}: {str(e)}")
        raise Exception(f"Instagram error: {str(e)}")

@api_router.post("/messages/analyze")
async def analyze_message(req: AnalyzeRequest):
    """Analyze message sentiment (simple rule-based, no LLM)"""
    logger.info(f"Analyzing message for contact {req.contact_id}")

    try:
        # Use simple sentiment analysis instead of LLM
        result = analyze_sentiment_simple(req.message)

        classification = result['classification']
        score = result['score']
        reason = result.get('reason', 'Analyzed using simple rules')

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

        logger.info(f"Analysis complete: {classification} ({score}/100)")
        return {"classification": classification, "score": score, "reason": reason}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Analysis failed: {str(e)}")

@api_router.get("/conversations")
async def get_conversations(current_user: User = Depends(get_current_user)):
    """Get positive and neutral conversations (requires authentication)"""
    logger.info(f"Fetching conversations for user {current_user.email}")
    try:
        contacts = await db.contacts.find(
            {"classification": {"$in": ["positive", "neutral"]}},
            {"_id": 0}
        ).to_list(1000)
        logger.info(f"Retrieved {len(contacts)} conversations")
        return contacts
    except Exception as e:
        logger.error(f"Failed to fetch conversations: {str(e)}")
        raise HTTPException(500, "Failed to fetch conversations")

@api_router.get("/conversations/{contact_id}")
async def get_conversation(contact_id: str):
    """Get conversation details"""
    logger.info(f"Fetching conversation for {contact_id}")

    if not validate_uuid(contact_id):
        raise HTTPException(400, "Invalid contact ID format")

    try:
        contact = await db.contacts.find_one({"id": contact_id}, {"_id": 0})
        if not contact:
            raise HTTPException(404, "Contact not found")

        messages = await db.messages.find(
            {"contact_id": contact_id},
            {"_id": 0}
        ).sort("timestamp", 1).to_list(1000)

        return {"contact": contact, "messages": messages}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch conversation: {str(e)}")
        raise HTTPException(500, "Failed to fetch conversation")

@api_router.post("/conversations/{contact_id}/message")
async def send_chat_message(contact_id: str, req: SendChatMessageRequest):
    """Send chat message"""
    logger.info(f"Sending chat message to {contact_id}")

    if not validate_uuid(contact_id):
        raise HTTPException(400, "Invalid contact ID format")

    try:
        contact = await db.contacts.find_one({"id": contact_id}, {"_id": 0})
        if not contact:
            raise HTTPException(404, "Contact not found")

        message = Message(
            contact_id=contact_id,
            content=req.message,
            direction="outbound"
        )
        await db.messages.insert_one(message.model_dump())

        return {"success": True, "message": message.model_dump()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send chat message: {str(e)}")
        raise HTTPException(500, "Failed to send message")

@api_router.get("/analytics")
async def get_analytics(current_user: User = Depends(get_current_user)):
    """Get analytics data (requires authentication)"""
    logger.info(f"Fetching analytics for user {current_user.email}")

    try:
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
    except Exception as e:
        logger.error(f"Failed to fetch analytics: {str(e)}")
        raise HTTPException(500, "Failed to fetch analytics")

# Refactored reset functions
async def reset_all_contacts():
    """Reset all contacts"""
    logger.info("Resetting all contacts")
    result = await db.contacts.update_many({}, {"$set": RESET_FIELDS})
    await db.categories.update_many({}, {"$set": {"sent_count": 0}})
    return result.modified_count

async def reset_category_contacts(category_id: str):
    """Reset contacts in specific category"""
    logger.info(f"Resetting category {category_id}")

    if not validate_uuid(category_id):
        raise HTTPException(400, "Invalid category ID format")

    result = await db.contacts.update_many(
        {"category_id": category_id},
        {"$set": RESET_FIELDS}
    )
    await db.categories.update_one(
        {"id": category_id},
        {"$set": {"sent_count": 0}}
    )
    return result.modified_count

async def reset_selected_contacts(contact_ids: List[str]):
    """Reset selected contacts"""
    logger.info(f"Resetting {len(contact_ids)} contacts")

    for contact_id in contact_ids:
        if not validate_uuid(contact_id):
            raise HTTPException(400, f"Invalid contact ID format: {contact_id}")

    result = await db.contacts.update_many(
        {"id": {"$in": contact_ids}},
        {"$set": RESET_FIELDS}
    )

    # Update category counters
    affected_contacts = await db.contacts.find(
        {"id": {"$in": contact_ids}},
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

    return result.modified_count

@api_router.post("/contacts/reset-status")
async def reset_contact_status(
    req: ResetStatusRequest,
    current_user: User = Depends(get_current_user)
):
    """Reset contact status (refactored, requires authentication)"""
    logger.info(f"Resetting contacts with scope: {req.scope} by user {current_user.email}")

    try:
        if req.scope == "all":
            reset_count = await reset_all_contacts()
        elif req.scope == "category":
            if not req.category_id:
                raise HTTPException(400, "category_id required for scope 'category'")
            reset_count = await reset_category_contacts(req.category_id)
        elif req.scope == "selected":
            if not req.contact_ids:
                raise HTTPException(400, "contact_ids required for scope 'selected'")
            reset_count = await reset_selected_contacts(req.contact_ids)
        else:
            raise HTTPException(400, "Invalid scope")

        logger.info(f"Reset {reset_count} contacts")

        return {
            "success": True,
            "reset_count": reset_count,
            "message": f"Reset {reset_count} contact(s) successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset failed: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Reset failed: {str(e)}")

# Include routers
app.include_router(api_router)

# Include auth router (with database injected)
auth_router = create_auth_router(db)
app.include_router(auth_router, prefix="/api")

# CORS configuration with validation
cors_origins = os.environ.get('CORS_ORIGINS', '*')
if cors_origins == '*':
    logger.warning("CORS configured with wildcard '*' - not recommended for production")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins.split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Startup event"""
    # Validate authentication configuration
    try:
        validate_auth_config()
        logger.info("Authentication configuration validated")
    except ValueError as e:
        logger.error(f"Authentication configuration error: {str(e)}")
        raise

    logger.info("Application started successfully")
    logger.info(f"MongoDB: {mongo_url}")
    logger.info(f"CORS origins: {cors_origins}")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Shutdown event"""
    logger.info("Shutting down application")
    client.close()
    logger.info("MongoDB connection closed")
