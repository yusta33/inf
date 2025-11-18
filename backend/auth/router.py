"""
Authentication API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import timedelta
import logging

from .models import UserCreate, UserLogin, User, UserResponse, Token
from .security import (
    hash_password,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from .dependencies import get_current_user_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def create_auth_router(db: AsyncIOMotorDatabase) -> APIRouter:
    """
    Create auth router with database dependency injected.

    Args:
        db: MongoDB database instance

    Returns:
        APIRouter with auth endpoints
    """
    # Create dependency for getting current user
    get_current_user = get_current_user_dependency(db)

    @router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
    async def register(user_data: UserCreate):
        """
        Register a new user.

        Args:
            user_data: User registration data

        Returns:
            Created user (without password)

        Raises:
            HTTPException: 400 if email already exists
        """
        logger.info(f"Registration attempt for email: {user_data.email}")

        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
        if existing_user:
            logger.warning(f"Registration failed: Email {user_data.email} already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash password
        password_hash = hash_password(user_data.password)

        # Create user object
        user = User(
            email=user_data.email,
            username=user_data.username or user_data.email.split('@')[0],
            password_hash=password_hash,
            roles=["user"],  # Default role
            is_active=True
        )

        # Insert into database
        try:
            await db.users.insert_one(user.model_dump())
            logger.info(f"User registered successfully: {user.email} (ID: {user.id})")
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )

        # Return user response (without password)
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            roles=user.roles,
            is_active=user.is_active,
            created_at=user.created_at
        )

    @router.post("/login", response_model=Token)
    async def login(credentials: UserLogin):
        """
        Login and get access token.

        Args:
            credentials: User login credentials

        Returns:
            JWT access token

        Raises:
            HTTPException: 401 if credentials are invalid
        """
        logger.info(f"Login attempt for email: {credentials.email}")

        # Get user from database
        user_data = await db.users.find_one({"email": credentials.email}, {"_id": 0})

        if not user_data:
            logger.warning(f"Login failed: User {credentials.email} not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = User(**user_data)

        # Verify password
        if not verify_password(credentials.password, user.password_hash):
            logger.warning(f"Login failed: Invalid password for {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login failed: User {credentials.email} is inactive")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "user_id": user.id,
                "email": user.email,
                "roles": user.roles
            },
            expires_delta=access_token_expires
        )

        logger.info(f"User logged in successfully: {user.email} (ID: {user.id})")

        return Token(access_token=access_token, token_type="bearer")

    @router.get("/me", response_model=UserResponse)
    async def get_me(current_user: User = Depends(get_current_user)):
        """
        Get current user profile.

        Args:
            current_user: Current authenticated user (from token)

        Returns:
            Current user data
        """
        logger.info(f"Profile request for user: {current_user.email}")

        return UserResponse(
            id=current_user.id,
            email=current_user.email,
            username=current_user.username,
            roles=current_user.roles,
            is_active=current_user.is_active,
            created_at=current_user.created_at
        )

    return router
