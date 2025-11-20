"""
Security utilities for password hashing and JWT token management.
"""

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
import os
import logging

from .models import User, TokenData

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# HTTP Bearer security scheme
security = HTTPBearer()


def hash_password(password: str) -> str:
    """
    Hash a plain password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary of data to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncIOMotorDatabase = None
) -> User:
    """
    Get the current authenticated user from JWT token.

    This dependency can be used to protect routes and get the current user.

    Args:
        credentials: HTTP Bearer credentials from request header
        db: MongoDB database instance

    Returns:
        Current authenticated User

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id: str = payload.get("user_id")
        email: str = payload.get("email")

        if user_id is None or email is None:
            logger.warning("Token missing user_id or email")
            raise credentials_exception

        token_data = TokenData(
            user_id=user_id,
            email=email,
            roles=payload.get("roles", ["user"])
        )

    except JWTError as e:
        logger.warning(f"JWT decode error: {str(e)}")
        raise credentials_exception

    # Get user from database
    if db is None:
        # This will be injected by dependency
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not available"
        )

    user_data = await db.users.find_one({"id": token_data.user_id}, {"_id": 0})

    if user_data is None:
        logger.warning(f"User {token_data.user_id} not found in database")
        raise credentials_exception

    user = User(**user_data)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


def require_role(required_role: str):
    """
    Dependency to require a specific role.

    Usage:
        @app.get("/admin/users", dependencies=[Depends(require_role("admin"))])

    Args:
        required_role: Role required to access the endpoint

    Returns:
        Dependency function
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if required_role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        return current_user

    return role_checker


def validate_auth_config():
    """
    Validate authentication configuration on startup.

    Raises:
        ValueError: If required auth configuration is missing or invalid
    """
    if not SECRET_KEY:
        raise ValueError("AUTH_SECRET_KEY environment variable must be set")

    if len(SECRET_KEY) < 32:
        logger.warning("AUTH_SECRET_KEY is shorter than recommended (32 characters)")

    if ACCESS_TOKEN_EXPIRE_MINUTES < 1:
        raise ValueError("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES must be at least 1")

    logger.info(f"Auth config validated: Token expiry = {ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
