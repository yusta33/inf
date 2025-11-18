"""
Authentication and authorization module for InboxHub CRM.

This module provides:
- User model and validation
- Password hashing and verification
- JWT token generation and validation
- Authentication dependencies for route protection
- Auth API endpoints (register, login, me)
"""

from .models import User, UserCreate, UserLogin, UserResponse, Token
from .security import hash_password, verify_password, create_access_token, get_current_user
from .router import router as auth_router

__all__ = [
    "User",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "Token",
    "hash_password",
    "verify_password",
    "create_access_token",
    "get_current_user",
    "auth_router",
]
