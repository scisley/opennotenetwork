"""
Authentication and authorization using Clerk
"""
import structlog
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import jwt
import httpx
from functools import lru_cache

from app.config import settings
from app.models import User

logger = structlog.get_logger()


@lru_cache(maxsize=1)
def get_clerk_public_key():
    """Get Clerk's public key for JWT verification (cached)"""
    # In production, this should fetch the JWKS from Clerk
    # For now, return a placeholder
    return "CLERK_PUBLIC_KEY_PLACEHOLDER"


async def verify_clerk_token(token: str) -> dict:
    """
    Verify Clerk JWT token
    
    This is a simplified implementation. In production, you should:
    1. Fetch Clerk's JWKS endpoint
    2. Verify the JWT signature
    3. Check token expiration and issuer
    """
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        
        # For development, we'll skip actual JWT verification
        # and just decode without verification (UNSAFE for production)
        decoded = jwt.decode(
            token, 
            options={"verify_signature": False}  # UNSAFE: Only for development
        )
        
        logger.debug("Token decoded", user_id=decoded.get("sub"))
        return decoded
        
    except jwt.InvalidTokenError as e:
        logger.error("Invalid JWT token", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    authorization: Optional[str],
    session: AsyncSession
) -> Optional[User]:
    """
    Get current user from authorization header
    
    Args:
        authorization: Authorization header value
        session: Database session
        
    Returns:
        User object or None if not authenticated
    """
    if not authorization:
        return None
    
    try:
        # Verify token with Clerk
        token_data = await verify_clerk_token(authorization)
        
        # Get user ID from token
        clerk_user_id = token_data.get("sub")
        if not clerk_user_id:
            return None
        
        # Get user email from token
        email = token_data.get("email")
        if not email:
            return None
        
        # Find or create user in our database
        result = await session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            user = User(
                email=email,
                display_name=token_data.get("name") or email,
                role="viewer"  # Default role
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            logger.info("Created new user", email=email, user_id=str(user.user_id))
        
        return user
        
    except Exception as e:
        logger.error("Authentication failed", error=str(e))
        return None


async def get_current_admin_user(
    authorization: Optional[str],
    session: AsyncSession
) -> User:
    """
    Get current user and verify admin role
    
    Args:
        authorization: Authorization header value
        session: Database session
        
    Returns:
        User object with admin role
        
    Raises:
        HTTPException: If not authenticated or not admin
    """
    user = await get_current_user(authorization, session)
    
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    
    return user


async def promote_user_to_admin(email: str, session: AsyncSession) -> bool:
    """
    Promote a user to admin role (for initial setup)
    
    Args:
        email: User email to promote
        session: Database session
        
    Returns:
        True if successful, False if user not found
    """
    try:
        from sqlalchemy import update
        
        result = await session.execute(
            update(User)
            .where(User.email == email)
            .values(role="admin")
            .returning(User.user_id)
        )
        
        user_id = result.scalar_one_or_none()
        
        if user_id:
            await session.commit()
            logger.info("User promoted to admin", email=email, user_id=str(user_id))
            return True
        else:
            logger.warning("User not found for promotion", email=email)
            return False
            
    except Exception as e:
        await session.rollback()
        logger.error("Failed to promote user", email=email, error=str(e))
        return False