"""
Authentication and authorization using Clerk
"""
import structlog
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer
import uuid

from app.models import User
from app.database import get_session
from app.config import settings

logger = structlog.get_logger()

# Configure Clerk authentication
clerk_config = ClerkConfig(
    jwks_url=settings.clerk_jwks_url
)

# Create the auth guard
clerk_auth_guard = ClerkHTTPBearer(config=clerk_config)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(clerk_auth_guard),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Get current user from JWT token and sync to database
    
    Args:
        credentials: JWT credentials from Clerk
        session: Database session
        
    Returns:
        User object from database
    """
    # Extract known fields from Clerk JWT
    decoded = credentials.decoded
    clerk_user_id = decoded.get("sub")  # Clerk user ID (always present)
    email = decoded.get("email")  # Email (configured in Clerk Dashboard session token)
    
    # Get role from metadata (configured in Clerk Dashboard session token)
    user_metadata = decoded.get("metadata", {})
    role = user_metadata.get("role", "viewer")
    
    # Use email as display name if no other name is available
    display_name = email or f"User {clerk_user_id}"
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not found in token. Ensure email is configured in Clerk Dashboard session token."
        )
    
    # Find or create user in database
    result = await session.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        logger.info("User not found, creating new user", email=email, role=role)
        
        # Create new user
        new_user_id = uuid.uuid4()
        user = User(
            user_id=new_user_id,
            email=email,
            clerk_user_id=clerk_user_id,
            display_name=display_name,
            role=role
        )
        session.add(user)
        
        try:
            await session.commit()
            await session.refresh(user)
            logger.info("Successfully created new user", 
                       email=email, 
                       user_id=str(user.user_id))
        except Exception as e:
            logger.error("Failed to create user", 
                        email=email, 
                        error=str(e))
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {str(e)}"
            )
    else:
        # Update role if changed (role comes from Clerk metadata)
        if user.role != role:
            logger.info("Updating user role", 
                       email=email, 
                       old_role=user.role,
                       new_role=role)
            user.role = role
            await session.commit()
            await session.refresh(user)
            logger.info("Role updated successfully", 
                       email=email,
                       updated_role=user.role)
    
    return user


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(clerk_auth_guard),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Require admin role for endpoint access
    
    Args:
        credentials: JWT credentials from Clerk
        session: Database session
        
    Returns:
        User object with admin role
        
    Raises:
        HTTPException: If user is not an admin
    """
    # Get the current user (this also validates the token and syncs to DB)
    user = await get_current_user(credentials, session)
    
    # Check if user has admin role
    if user.role != "admin":
        logger.warning("Non-admin user attempted admin access", 
                      email=user.email,
                      role=user.role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required"
        )
    
    return user


# Create optional auth guard
clerk_auth_guard_optional = ClerkHTTPBearer(config=clerk_config, auto_error=False)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(clerk_auth_guard_optional),
    session: AsyncSession = Depends(get_session)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None
    Used for endpoints that work with or without authentication
    
    Args:
        credentials: Optional JWT credentials from Clerk
        session: Database session
        
    Returns:
        User object or None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, session)
    except Exception as e:
        logger.debug("Optional auth failed", error=str(e))
        return None