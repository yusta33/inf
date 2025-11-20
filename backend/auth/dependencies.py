"""
Authentication dependencies for FastAPI dependency injection.
"""

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase

from .models import User
from .security import get_current_user as get_user_from_token

# HTTP Bearer security scheme
security = HTTPBearer()


# We'll use a factory pattern to inject the database
def get_current_user_dependency(db: AsyncIOMotorDatabase):
    """
    Create a dependency function that gets the current user with database access.

    This is a factory function that returns the actual dependency.

    Args:
        db: MongoDB database instance

    Returns:
        Dependency function that can be used with Depends()
    """
    async def _get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> User:
        return await get_user_from_token(credentials, db)

    return _get_current_user


def require_role_dependency(db: AsyncIOMotorDatabase, required_role: str):
    """
    Create a dependency that requires a specific role.

    Args:
        db: MongoDB database instance
        required_role: Role required to access the endpoint

    Returns:
        Dependency function
    """
    async def _role_checker(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> User:
        user = await get_user_from_token(credentials, db)

        if required_role not in user.roles:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )

        return user

    return _role_checker
