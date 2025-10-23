"""
Resource endpoints with role-based access control.
These endpoints adapt their responses based on the caller's authentication/role.
"""
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_optional_user
from app.database import get_session
from app.models import Classifier, FactCheck, FactChecker, Post, User
from app.schemas.public import (
    ClassifierPublicResponse,
    FactCheckerPublicResponse,
    FactCheckPublicResponse,
)
from app.services import note_writing

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


@router.get("/fact-checkers")
async def get_fact_checkers(
    is_active: Optional[bool] = Query(None),
    current_user: Optional[User] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get list of available fact checkers.

    Response varies based on authentication:
    - Public users: Only see active fact checkers
    - Admins: See all fact checkers with ability to filter
    """
    try:
        query = select(FactChecker)

        # For non-admin users, only show active fact checkers
        if not current_user or current_user.role != "admin":
            query = query.where(FactChecker.is_active == True)
        elif is_active is not None:
            # Admins can filter by active status
            query = query.where(FactChecker.is_active == is_active)

        # Order by name
        query = query.order_by(FactChecker.name)

        result = await session.execute(query)
        fact_checkers = result.scalars().all()

        # Convert to response models
        fact_checker_responses = []
        for checker in fact_checkers:
            response = FactCheckerPublicResponse(
                id=str(checker.fact_checker_id),
                slug=checker.slug,
                name=checker.name,
                description=checker.description,
                version=checker.version,
                is_active=checker.is_active,
                created_at=checker.created_at,
                updated_at=checker.updated_at
            )
            fact_checker_responses.append(response)

        return {
            "fact_checkers": fact_checker_responses,
            "total": len(fact_checker_responses)
        }

    except Exception as e:
        logger.error("Failed to get fact checkers", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/posts/{post_uid}/fact-checks")
async def get_post_fact_checks(
    post_uid: str,
    current_user: Optional[User] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get fact checks for a specific post.

    Response varies based on authentication:
    - Public users: Only see completed fact checks
    - Admins: See all fact checks including pending/failed
    """
    try:
        # First verify the post exists
        post_result = await session.execute(
            select(Post).where(Post.post_uid == post_uid)
        )
        post = post_result.scalar_one_or_none()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # Build query for fact checks with fact checker info
        query = select(FactCheck, FactChecker).join(
            FactChecker, FactCheck.fact_checker_id == FactChecker.fact_checker_id
        ).where(FactCheck.post_uid == post_uid)

        # For non-admin users, only show completed and ineligible fact checks
        # (hide pending, processing, and failed statuses)
        if not current_user or current_user.role != "admin":
            query = query.where(FactCheck.status.in_(["completed", "ineligible"]))

        # Order by creation date
        query = query.order_by(FactCheck.created_at.desc())

        result = await session.execute(query)
        fact_checks_with_checkers = result.all()

        # Convert to response models
        fact_check_responses = []
        for fact_check, fact_checker in fact_checks_with_checkers:
            # Create fact checker response
            checker_response = FactCheckerPublicResponse(
                id=str(fact_checker.fact_checker_id),
                slug=fact_checker.slug,
                name=fact_checker.name,
                description=fact_checker.description,
                version=fact_checker.version,
                is_active=fact_checker.is_active,
                created_at=fact_checker.created_at,
                updated_at=fact_checker.updated_at
            )

            # Create fact check response
            # For admin users, include raw_json; for others, exclude it
            check_response = FactCheckPublicResponse(
                id=str(fact_check.fact_check_id),
                post_uid=fact_check.post_uid,
                fact_checker=checker_response,
                body=fact_check.body,
                raw_json=fact_check.raw_json if current_user and current_user.role == "admin" else None,
                verdict=fact_check.verdict,
                confidence=float(fact_check.confidence) if fact_check.confidence else None,
                claims=fact_check.claims,
                status=fact_check.status,
                error_message=fact_check.error_message,
                created_at=fact_check.created_at,
                updated_at=fact_check.updated_at
            )
            fact_check_responses.append(check_response)

        return {
            "fact_checks": fact_check_responses,
            "total": len(fact_check_responses)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get fact checks", post_uid=post_uid, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/note-writers")
async def get_note_writers(
    is_active: Optional[bool] = Query(None),
    platform: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get list of available note writers.

    Response varies based on authentication:
    - Public users: Only see active note writers
    - Admins: See all note writers with full details
    """
    try:
        # Get all note writers from the service
        all_writers = await note_writing.list_available_note_writers()

        # Filter based on user role
        filtered_writers = []
        for writer in all_writers:
            # For non-admin users, only show active and available writers
            if not current_user or current_user.role != "admin":
                if writer.get("available") and writer.get("in_database"):
                    # Check if active in database
                    if is_active is None or is_active:
                        filtered_writers.append(writer)
            else:
                # Admins see all writers, can filter by active status
                if is_active is not None:
                    # If filtering by active, only include those that match
                    if writer.get("available") == is_active or writer.get("in_database"):
                        filtered_writers.append(writer)
                else:
                    filtered_writers.append(writer)

        # Filter by platform if specified
        if platform:
            filtered_writers = [
                w for w in filtered_writers
                if platform in w.get("platforms", [])
            ]

        return {
            "note_writers": filtered_writers,
            "total": len(filtered_writers)
        }

    except Exception as e:
        logger.error("Failed to get note writers", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/fact-checks/{fact_check_id}/notes")
async def get_fact_check_notes(
    fact_check_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get notes for a specific fact check.

    Response varies based on authentication:
    - Public users: Only see completed notes
    - Admins: See all notes including pending/failed
    """
    try:
        # Get all notes for the fact check
        all_notes = await note_writing.get_notes_for_fact_check(fact_check_id)

        # Filter based on user role
        if not current_user or current_user.role != "admin":
            # Public users only see completed notes
            filtered_notes = [
                note for note in all_notes
                if note.get("status") == "completed"
            ]
        else:
            # Admins see all notes
            filtered_notes = all_notes

        return {
            "notes": filtered_notes,
            "total": len(filtered_notes)
        }

    except Exception as e:
        logger.error("Failed to get notes", fact_check_id=fact_check_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
