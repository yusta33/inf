"""
User models and validation schemas for authentication.
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import re


class UserBase(BaseModel):
    """Base user model with common fields"""
    email: EmailStr
    username: Optional[str] = None


class UserCreate(UserBase):
    """Model for user registration"""
    password: str
    confirm_password: str

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Ensure password and confirm_password match"""
        if 'password' in values and v != values['password']:
            raise ValueError("Passwords do not match")
        return v

    @validator('email')
    def validate_email_format(cls, v):
        """Additional email validation"""
        if not v or '@' not in v:
            raise ValueError("Invalid email format")
        return v.lower()


class UserLogin(BaseModel):
    """Model for user login"""
    email: EmailStr
    password: str

    @validator('email')
    def normalize_email(cls, v):
        """Normalize email to lowercase"""
        return v.lower()


class User(UserBase):
    """Complete user model stored in database"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    password_hash: str
    roles: List[str] = Field(default_factory=lambda: ["user"])
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    class Config:
        extra = "ignore"


class UserResponse(UserBase):
    """User response model (without sensitive data)"""
    id: str
    roles: List[str]
    is_active: bool
    created_at: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data stored in JWT token"""
    user_id: str
    email: str
    roles: List[str]
