"""
Resource endpoints with role-based access control.
These endpoints adapt their responses based on the caller's authentication/role.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
import structlog

from app.database import get_session
from app.models import Classifier, User, Classification
from app.schemas.public import ClassifierPublicResponse
from app.auth import get_optional_user

logger = structlog.get_logger()

router = APIRouter()


@router.get("/classifiers")
async def get_classifiers(
    is_active: Optional[bool] = Query(None),
    group_name: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get list of available classifiers.
    
    Response varies based on authentication:
    - Public users: Only see active classifiers, basic info
    - Admins: See all classifiers with full details
    """
    try:
        query = select(Classifier)
        
        # For non-admin users, only show active classifiers by default
        if not current_user or current_user.role != "admin":
            # Public users only see active classifiers
            query = query.where(Classifier.is_active == True)
        elif is_active is not None:
            # Admins can filter by active status
            query = query.where(Classifier.is_active == is_active)
        
        # Apply group filter
        if group_name:
            query = query.where(Classifier.group_name == group_name)
        
        # Order by group name then display name
        query = query.order_by(
            Classifier.group_name.nullsfirst(),
            Classifier.display_name
        )
        
        result = await session.execute(query)
        classifiers = result.scalars().all()
        
        # Convert to response models - everyone gets the same base response
        classifier_responses = []
        for classifier in classifiers:
            response = ClassifierPublicResponse(
                classifier_id=str(classifier.classifier_id),
                slug=classifier.slug,
                display_name=classifier.display_name,
                description=classifier.description,
                group_name=classifier.group_name,
                is_active=classifier.is_active,
                output_schema=classifier.output_schema,
                created_at=classifier.created_at,
                updated_at=classifier.updated_at
            )
            classifier_responses.append(response)
        
        return {
            "classifiers": classifier_responses,
            "total": len(classifier_responses)
        }
        
    except Exception as e:
        logger.error("Failed to get classifiers", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/classifiers/{slug}")
async def get_classifier(
    slug: str,
    current_user: Optional[User] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get a specific classifier by slug.
    
    Response varies based on authentication:
    - Public users: Only see active classifiers
    - Admins: Can see all classifiers
    """
    try:
        query = select(Classifier).where(Classifier.slug == slug)
        
        # Public users can only see active classifiers
        if not current_user or current_user.role != "admin":
            query = query.where(Classifier.is_active == True)
        
        result = await session.execute(query)
        classifier = result.scalar_one_or_none()
        
        if not classifier:
            raise HTTPException(status_code=404, detail="Classifier not found")
        
        # Everyone gets the same base response
        return ClassifierPublicResponse(
            classifier_id=str(classifier.classifier_id),
            slug=classifier.slug,
            display_name=classifier.display_name,
            description=classifier.description,
            group_name=classifier.group_name,
            is_active=classifier.is_active,
            output_schema=classifier.output_schema,
            created_at=classifier.created_at,
            updated_at=classifier.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get classifier", slug=slug, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")