import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, get_optional_user, require_admin
from app.database import get_session
from app.models import (
    Classification,
    Classifier,
    FactCheck,
    FactChecker,
    Note,
    NoteWriter,
    Post,
    PostTopic,
    Submission,
    Topic,
    User,
)
from app.schemas.admin import (
    BatchFactCheckJobStatus,
    BatchFactCheckResponse,
    ClassificationCreate,
    ClassificationResponse,
    ClassifierCreate,
    ClassifierResponse,
    ClassifierUpdate,
    EditNoteRequest,
    EditNoteResponse,
    FactCheckEligibleCountResponse,
    PostDetailResponse,
    SubmitNoteResponse,
    UpdateStatusesResponse,
    SubmissionsSummaryResponse,
    SubmissionQueueItem,
    SubmissionQueueResponse,
    WritingLimitResponse,
)
from app.services import classification, fact_checking, ingestion, note_writing, submission
from app.services.evaluation import evaluate_note


def parse_iso_dates(start_date: str, end_date: str) -> tuple[datetime, datetime]:
    """Parse ISO date strings, handling 'Z' timezone indicator"""
    start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    return start, end

logger = structlog.get_logger()

router = APIRouter()


# Debug endpoint to test authentication
@router.get("/auth-test")
async def test_authentication(
    current_user: User = Depends(get_current_user)
):
    """Test endpoint to verify authentication is working"""
    return {
        "authenticated": True,
        "user_id": str(current_user.user_id),
        "email": current_user.email,
        "role": current_user.role,
        "display_name": current_user.display_name
    }


@router.get("/admin-test")
async def test_admin_authentication(
    current_user: User = Depends(require_admin)
):
    """Test endpoint to verify admin authentication is working"""
    return {
        "authenticated": True,
        "is_admin": True,
        "user_id": str(current_user.user_id),
        "email": current_user.email,
        "role": current_user.role
    }


@router.get("/users-check")
async def check_users_table(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin)
):
    """Check all users in the database"""
    result = await session.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    return {
        "total_users": len(users),
        "users": [
            {
                "user_id": str(user.user_id),
                "email": user.email,
                "display_name": user.display_name,
                "role": user.role,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in users
        ]
    }


# Ingestion with job tracking
ingestion_jobs = {}  # Store job status in memory

@router.post("/ingest")
async def trigger_ingestion(
    batch_size: int = 50,
    max_total_posts: int = 500,
    duplicate_threshold: float = 0.7,
    auto_classify: bool = True,
    classifier_slugs: Optional[list[str]] = Query(None),
    user: Optional[User] = Depends(get_optional_user)
):
    """Trigger async ingestion with job tracking"""
    import asyncio
    from datetime import datetime

    job_id = str(uuid.uuid4())

    # Initialize job status
    ingestion_jobs[job_id] = {
        "job_id": job_id,
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "batch_size": batch_size,
        "max_total_posts": max_total_posts,
        "new_posts": 0,
        "updated_posts": 0,
        "posts_processed": 0,
        "duplicate_ratio": 0.0,
        "current_batch": 0,
        "message": "Starting ingestion...",
        "errors": []
    }

    async def run_ingestion_job():
        # Create a new database session for the background task
        from app.database import async_session_factory

        async with async_session_factory() as bg_session:
            try:
                # Update status to indicate we're fetching
                ingestion_jobs[job_id]["message"] = "Fetching posts from X.com..."

                result = await ingestion.run_ingestion(
                    bg_session,
                    batch_size=batch_size,
                    max_total_posts=max_total_posts,
                    duplicate_threshold=duplicate_threshold,
                    auto_classify=auto_classify,
                    classifier_slugs=classifier_slugs
                )

                # Update job with results
                ingestion_jobs[job_id].update({
                    "status": "completed",
                    "completed_at": datetime.utcnow().isoformat(),
                    "new_posts": result.get("new_posts", result.get("added", 0)),
                    "updated_posts": result.get("updated_posts", 0),
                    "posts_processed": result.get("posts_processed", result.get("added", 0) + result.get("skipped", 0)),
                    "duplicate_ratio": result.get("duplicate_ratio", 0.0),
                    "message": result.get("message", "Ingestion completed successfully")
                })
            except Exception as e:
                logger.error("Async ingestion failed", job_id=job_id, error=str(e))
                ingestion_jobs[job_id].update({
                    "status": "failed",
                    "completed_at": datetime.utcnow().isoformat(),
                    "message": f"Ingestion failed: {str(e)}",
                    "errors": [str(e)]
                })

    # Start the job in the background
    asyncio.create_task(run_ingestion_job())

    logger.info("Started async ingestion job", job_id=job_id)

    return {
        "job_id": job_id,
        "status": "started",
        "message": "Ingestion job started"
    }


@router.get("/ingest/{job_id}/status")
async def get_ingestion_job_status(
    job_id: str,
    user: User = Depends(require_admin)
):
    """Get the status of an async ingestion job"""
    if job_id not in ingestion_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return ingestion_jobs[job_id]


@router.post("/test-x-auth")
async def test_x_auth(
    user: User = Depends(require_admin)
):
    """Test X.com API authentication with a simple endpoint"""
    from app.config import settings
    from app.services.x_api_client import get_x_api_client

    # Debug: Show what credentials we're actually using (partially masked)
    debug_info = {
        "api_key_preview": settings.x_api_key[:10] + "..." if settings.x_api_key else "MISSING",
        "api_secret_preview": settings.x_api_key_secret[:10] + "..." if settings.x_api_key_secret else "MISSING",
        "token_preview": settings.x_access_token[:10] + "..." if settings.x_access_token else "MISSING",
        "token_secret_preview": settings.x_access_token_secret[:10] + "..." if settings.x_access_token_secret else "MISSING"
    }

    try:
        # Get the shared X API client
        client = get_x_api_client()

        # Make authenticated request to /2/users/me
        response = client.get("/2/users/me", timeout=30)

        if not response.ok:
            return {
                "status": "error",
                "error": f"X.com API request failed with status {response.status_code}",
                "response": response.text[:500],
                "debug": debug_info
            }

        data = response.json()
        return {"status": "success", "user": data, "debug": debug_info}
    except Exception as e:
        return {"status": "error", "error": str(e), "debug": debug_info}


# Topic management endpoints (legacy - kept for backward compatibility)
@router.post("/posts/{post_uid}/topics")
async def add_manual_topic(
    post_uid: str,
    topic_slug: str,
    confidence: Optional[float] = None,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """Manually add topic to a post"""
    try:
        # Get topic
        topic_result = await session.execute(
            select(Topic).where(Topic.slug == topic_slug)
        )
        topic = topic_result.scalar_one_or_none()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        # Upsert post_topic
        from app.models import PostTopic
        post_topic = PostTopic(
            post_uid=post_uid,
            topic_id=topic.topic_id,
            labeled_by="admin",
            confidence=confidence
        )

        # Use merge to handle upsert
        session.merge(post_topic)
        await session.commit()

        return {"message": "Topic added successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add manual topic", post_uid=post_uid, topic=topic_slug, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to add topic")


@router.delete("/posts/{post_uid}/topics/{topic_slug}")
async def remove_topic(
    post_uid: str,
    topic_slug: str,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """Remove topic from a post"""
    try:
        # Get topic
        topic_result = await session.execute(
            select(Topic).where(Topic.slug == topic_slug)
        )
        topic = topic_result.scalar_one_or_none()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        # Delete post_topic
        await session.execute(
            update(PostTopic)
            .where(and_(PostTopic.post_uid == post_uid, PostTopic.topic_id == topic.topic_id))
        )
        await session.commit()

        return {"message": "Topic removed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to remove topic", post_uid=post_uid, topic=topic_slug, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to remove topic")





# Batch reclassification endpoints
@router.get("/posts-date-range/count")
async def count_posts_by_date_range(
    start_date: str,  # ISO format: 2024-01-01T00:00:00
    end_date: str,    # ISO format: 2024-01-31T23:59:59
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Count posts within a date range based on ingested_at timestamp"""
    try:
        # Parse dates
        start, end = parse_iso_dates(start_date, end_date)

        # Count posts in range
        count_result = await session.execute(
            select(func.count(Post.post_uid))
            .where(and_(
                Post.ingested_at >= start,
                Post.ingested_at <= end
            ))
        )
        count = count_result.scalar() or 0

        return {
            "start_date": start_date,
            "end_date": end_date,
            "post_count": count
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error("Failed to count posts by date range", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to count posts")


# Admin data endpoints
@router.get("/posts/{post_uid}", response_model=PostDetailResponse)
async def get_post_detail(
    post_uid: str,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get detailed post information for admin"""
    try:
        # Get post with all related data
        query = (
            select(Post)
            .where(Post.post_uid == post_uid)
        )
        result = await session.execute(query)
        post = result.scalar_one_or_none()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # Get topics
        topic_query = (
            select(PostTopic, Topic)
            .join(Topic)
            .where(PostTopic.post_uid == post_uid)
        )
        topic_result = await session.execute(topic_query)
        topics = [
            {
                "slug": topic.slug,
                "display_name": topic.display_name,
                "confidence": post_topic.confidence,
                "labeled_by": post_topic.labeled_by
            }
            for post_topic, topic in topic_result.fetchall()
        ]

        # Get submissions (via notes and fact_checks)
        submission_query = (
            select(Submission)
            .join(Note, Note.note_id == Submission.note_id)
            .join(FactCheck, FactCheck.fact_check_id == Note.fact_check_id)
            .where(FactCheck.post_uid == post_uid)
            .order_by(Submission.submitted_at.desc())
        )
        submission_result = await session.execute(submission_query)
        submissions = submission_result.scalars().all()

        return PostDetailResponse(
            post_uid=post.post_uid,
            platform=post.platform,
            platform_post_id=post.platform_post_id,
            author_handle=post.author_handle,
            text=post.text,
            created_at=post.created_at,
            ingested_at=post.ingested_at,
            last_error=post.last_error,
            topics=topics,
            classifications=[],  # TODO: Add classifications to admin detail
            drafts=[],
            submissions=[
                {
                    "submission_id": str(submission.submission_id),
                    "x_note_id": submission.x_note_id,
                    "status": submission.status,
                    "submitted_at": submission.submitted_at
                }
                for submission in submissions
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get post detail", post_uid=post_uid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get post detail")


# Classifier management endpoints (CREATE, UPDATE, DELETE only - GET moved to /api/classifiers)
@router.post("/classifiers", response_model=ClassifierResponse)
async def create_classifier(
    request: ClassifierCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Create a new classifier"""
    try:
        # Check if slug already exists
        existing = await session.execute(
            select(Classifier).where(Classifier.slug == request.slug)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Classifier slug already exists")

        classifier = Classifier(
            slug=request.slug,
            display_name=request.display_name,
            description=request.description,
            group_name=request.group_name,
            is_active=request.is_active,
            output_schema=request.output_schema,
            config=request.config
        )

        session.add(classifier)
        await session.commit()
        await session.refresh(classifier)

        return ClassifierResponse(
            classifier_id=str(classifier.classifier_id),
            slug=classifier.slug,
            display_name=classifier.display_name,
            description=classifier.description,
            group_name=classifier.group_name,
            is_active=classifier.is_active,
            output_schema=classifier.output_schema,
            config=classifier.config or {},
            created_at=classifier.created_at,
            updated_at=classifier.updated_at,
            classification_count=0
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("Failed to create classifier", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create classifier")


@router.patch("/classifiers/{slug}", response_model=ClassifierResponse)
async def update_classifier(
    slug: str,
    request: ClassifierUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Update an existing classifier"""
    try:
        result = await session.execute(
            select(Classifier).where(Classifier.slug == slug)
        )
        classifier = result.scalar_one_or_none()

        if not classifier:
            raise HTTPException(status_code=404, detail="Classifier not found")

        # Update fields if provided
        if request.display_name is not None:
            classifier.display_name = request.display_name
        if request.description is not None:
            classifier.description = request.description
        if request.group_name is not None:
            classifier.group_name = request.group_name
        if request.is_active is not None:
            classifier.is_active = request.is_active
        if request.output_schema is not None:
            classifier.output_schema = request.output_schema
        if request.config is not None:
            classifier.config = request.config

        await session.commit()
        await session.refresh(classifier)

        # Count classifications
        count_result = await session.execute(
            select(func.count(Classification.classification_id))
            .where(Classification.classifier_slug == slug)
        )
        count = count_result.scalar() or 0

        return ClassifierResponse(
            classifier_id=str(classifier.classifier_id),
            slug=classifier.slug,
            display_name=classifier.display_name,
            description=classifier.description,
            group_name=classifier.group_name,
            is_active=classifier.is_active,
            output_schema=classifier.output_schema,
            config=classifier.config or {},
            created_at=classifier.created_at,
            updated_at=classifier.updated_at,
            classification_count=count
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("Failed to update classifier", slug=slug, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update classifier")


@router.delete("/classifiers/{slug}")
async def delete_classifier(
    slug: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Delete a classifier (will also delete all its classifications)"""
    try:
        result = await session.execute(
            select(Classifier).where(Classifier.slug == slug)
        )
        classifier = result.scalar_one_or_none()

        if not classifier:
            raise HTTPException(status_code=404, detail="Classifier not found")

        # Check if there are classifications
        count_result = await session.execute(
            select(func.count(Classification.classification_id))
            .where(Classification.classifier_slug == slug)
        )
        count = count_result.scalar() or 0

        if count > 0:
            # Optionally prevent deletion if classifications exist
            # raise HTTPException(status_code=400, detail=f"Cannot delete classifier with {count} existing classifications")
            logger.warning(f"Deleting classifier {slug} with {count} classifications")

        await session.delete(classifier)
        await session.commit()

        return {"message": f"Classifier {slug} deleted successfully", "classifications_deleted": count}

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("Failed to delete classifier", slug=slug, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete classifier")


# Classification endpoints
@router.get("/posts/{post_uid}/classifications", response_model=list[ClassificationResponse])
async def get_post_classifications(
    post_uid: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Get all classifications for a post"""
    try:
        query = (
            select(Classification, Classifier)
            .join(Classifier, Classification.classifier_slug == Classifier.slug)
            .where(Classification.post_uid == post_uid)
            .order_by(Classification.created_at.desc())
        )

        result = await session.execute(query)
        classifications = []

        for classification, classifier in result.fetchall():
            classifications.append(ClassificationResponse(
                classification_id=str(classification.classification_id),
                post_uid=classification.post_uid,
                classifier_slug=classification.classifier_slug,
                classifier_display_name=classifier.display_name,
                classification_data=classification.classification_data,
                created_at=classification.created_at,
                updated_at=classification.updated_at
            ))

        return classifications

    except Exception as e:
        logger.error("Failed to get post classifications", post_uid=post_uid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get classifications")


@router.post("/posts/{post_uid}/classify")
async def classify_post(
    post_uid: str,
    classifier_slugs: Optional[list[str]] = Query(None),
    force: bool = Query(True),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """
    Run classifiers on a specific post

    Args:
        post_uid: The post to classify
        classifier_slugs: Optional list of specific classifier slugs to run.
                         If not provided, runs all active classifiers.
        force: If True, overwrites existing classifications (default: True)
    """
    try:
        logger.info(f"Classify request - post_uid: {post_uid}, classifier_slugs: {classifier_slugs}, force: {force}")

        # If force, delete existing classifications first
        if force:
            if classifier_slugs:
                # Delete only specific classifications
                for slug in classifier_slugs:
                    await session.execute(
                        Classification.__table__.delete().where(
                            and_(
                                Classification.post_uid == post_uid,
                                Classification.classifier_slug == slug
                            )
                        )
                    )
            else:
                # Delete all classifications for this post
                await session.execute(
                    Classification.__table__.delete().where(
                        Classification.post_uid == post_uid
                    )
                )
            await session.commit()

        # Run classification
        result = await classification.classify_post(
            post_uid=post_uid,
            classifier_slugs=classifier_slugs
        )

        return {
            "post_uid": post_uid,
            "classified": result.get("classified", 0),
            "skipped": result.get("skipped", 0),
            "errors": result.get("errors", [])
        }

    except Exception as e:
        logger.error("Failed to classify post", post_uid=post_uid, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to classify post: {str(e)}")


@router.post("/posts/classify-batch")
async def classify_posts_batch(
    post_uids: list[str],
    classifier_slugs: Optional[list[str]] = Query(None),
    force: bool = Query(True),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """
    Run classifiers on multiple posts

    Args:
        post_uids: List of post UIDs to classify
        classifier_slugs: Optional list of specific classifier slugs to run.
                         If not provided, runs all active classifiers.
        force: If True, overwrites existing classifications (default: True)
    """
    try:
        # If force, delete existing classifications first
        if force:
            for post_uid in post_uids:
                if classifier_slugs:
                    # Delete only specific classifications
                    for slug in classifier_slugs:
                        await session.execute(
                            Classification.__table__.delete().where(
                                and_(
                                    Classification.post_uid == post_uid,
                                    Classification.classifier_slug == slug
                                )
                            )
                        )
                else:
                    # Delete all classifications for this post
                    await session.execute(
                        Classification.__table__.delete().where(
                            Classification.post_uid == post_uid
                        )
                    )
            await session.commit()

        # Run batch classification
        result = await classification.classify_posts_batch(
            post_uids=post_uids,
            classifier_slugs=classifier_slugs
        )

        return result

    except Exception as e:
        logger.error("Failed to classify posts batch", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to classify posts: {str(e)}")


@router.post("/classifications", response_model=ClassificationResponse)
async def create_classification(
    request: ClassificationCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Manually create a classification (for testing)"""
    try:
        # Check if post exists
        post_result = await session.execute(
            select(Post).where(Post.post_uid == request.post_uid)
        )
        if not post_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Post not found")

        # Check if classifier exists
        classifier_result = await session.execute(
            select(Classifier).where(Classifier.slug == request.classifier_slug)
        )
        classifier = classifier_result.scalar_one_or_none()
        if not classifier:
            raise HTTPException(status_code=404, detail="Classifier not found")

        # Check if classification already exists
        existing = await session.execute(
            select(Classification)
            .where(and_(
                Classification.post_uid == request.post_uid,
                Classification.classifier_slug == request.classifier_slug
            ))
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Classification already exists for this post and classifier")

        classification = Classification(
            post_uid=request.post_uid,
            classifier_slug=request.classifier_slug,
            classification_data=request.classification_data
        )

        session.add(classification)
        await session.commit()
        await session.refresh(classification)

        return ClassificationResponse(
            classification_id=str(classification.classification_id),
            post_uid=classification.post_uid,
            classifier_slug=classification.classifier_slug,
            classifier_display_name=classifier.display_name,
            classification_data=classification.classification_data,
            created_at=classification.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("Failed to create classification", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create classification")


# Batch reclassification endpoint
@router.post("/batch-reclassify")
async def batch_reclassify_posts(
    start_date: str,
    end_date: str,
    classifier_slugs: Optional[list[str]] = Query(None),
    force: bool = Query(True),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """
    Trigger batch reclassification of posts within a date range

    Args:
        start_date: Start date in ISO format
        end_date: End date in ISO format
        classifier_slugs: Optional list of specific classifier slugs to run
        force: Whether to overwrite existing classifications
    """
    try:
        import asyncio

        # Parse dates
        start, end = parse_iso_dates(start_date, end_date)

        # Get posts in date range
        posts_result = await session.execute(
            select(Post.post_uid)
            .where(and_(
                Post.ingested_at >= start,
                Post.ingested_at <= end
            ))
        )
        post_uids = [row[0] for row in posts_result.fetchall()]

        if not post_uids:
            return {
                "message": "No posts found in date range",
                "total_posts": 0,
                "classified": 0,
                "errors": []
            }

        # Create a background task ID for tracking
        import uuid
        job_id = str(uuid.uuid4())

        # Store job info in memory (in production, use Redis or DB)
        from app.services import classification_jobs
        classification_jobs.create_job(job_id, len(post_uids))

        # Start background task (it will create its own session)
        asyncio.create_task(
            classification_jobs.run_batch_classification(
                job_id=job_id,
                post_uids=post_uids,
                classifier_slugs=classifier_slugs,
                force=force
            )
        )

        return {
            "job_id": job_id,
            "total_posts": len(post_uids),
            "status": "started",
            "message": f"Started batch classification for {len(post_uids)} posts"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error("Failed to start batch reclassification", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start batch reclassification")


@router.get("/batch-reclassify/{job_id}/status")
async def get_batch_job_status(
    job_id: str,
    user: User = Depends(require_admin)
):
    """Get the status of a batch reclassification job"""
    try:
        from app.services import classification_jobs

        job_status = classification_jobs.get_job_status(job_id)
        if not job_status:
            raise HTTPException(status_code=404, detail="Job not found")

        return job_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job status", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get job status")


# Fact Checker endpoints - Mutations only (GET endpoints moved to resources.py)
@router.post("/posts/{post_uid}/fact-check/{fact_checker_slug}")
async def run_fact_check_on_post(
    post_uid: str,
    fact_checker_slug: str,
    force: bool = False,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Run a specific fact checker on a post"""
    try:
        result = await fact_checking.run_fact_check(
            post_uid=post_uid,
            fact_checker_slug=fact_checker_slug,
            force=force
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to run fact check",
                    post_uid=post_uid,
                    fact_checker=fact_checker_slug,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to run fact check")


@router.get("/fact-checks/{fact_check_id}/status")
async def get_fact_check_status(
    fact_check_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Get the status of a fact check job"""
    try:
        status = await fact_checking.get_fact_check_status(fact_check_id)
        if not status:
            raise HTTPException(status_code=404, detail="Fact check not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get fact check status", fact_check_id=fact_check_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get fact check status")


@router.delete("/posts/{post_uid}/fact-check/{fact_checker_slug}")
async def delete_fact_check(
    post_uid: str,
    fact_checker_slug: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Delete a fact check result to allow rerunning"""
    try:
        # Get the fact checker
        result = await session.execute(
            select(FactChecker).where(FactChecker.slug == fact_checker_slug)
        )
        fact_checker = result.scalar_one_or_none()

        if not fact_checker:
            raise HTTPException(status_code=404, detail="Fact checker not found")

        # Delete the fact check
        result = await session.execute(
            select(FactCheck).where(
                and_(
                    FactCheck.post_uid == post_uid,
                    FactCheck.fact_checker_id == fact_checker.fact_checker_id
                )
            )
        )
        fact_check = result.scalar_one_or_none()

        if not fact_check:
            raise HTTPException(status_code=404, detail="Fact check not found")

        await session.delete(fact_check)
        await session.commit()

        return {"message": "Fact check deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete fact check",
                    post_uid=post_uid,
                    fact_checker=fact_checker_slug,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete fact check")


# Note Writer endpoints - Mutations only
@router.post("/fact-checks/{fact_check_id}/note/{note_writer_slug}")
async def run_note_writer_on_fact_check(
    fact_check_id: str,
    note_writer_slug: str,
    force: bool = False,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Run a specific note writer on a fact check"""
    try:
        result = await note_writing.write_note(
            fact_check_id=fact_check_id,
            note_writer_slug=note_writer_slug,
            force=force
        )
        return result
    except ValueError as e:
        logger.error(f"Note writer error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error running note writer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/fact-checks/{fact_check_id}/note/{note_writer_slug}")
async def delete_note(
    fact_check_id: str,
    note_writer_slug: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Delete a note to allow rerunning"""
    try:
        # Get the note writer
        result = await session.execute(
            select(NoteWriter).where(NoteWriter.slug == note_writer_slug)
        )
        note_writer = result.scalar_one_or_none()

        if not note_writer:
            raise HTTPException(status_code=404, detail=f"Note writer {note_writer_slug} not found")

        # Find the note
        result = await session.execute(
            select(Note).where(
                and_(
                    Note.fact_check_id == uuid.UUID(fact_check_id),
                    Note.note_writer_id == note_writer.note_writer_id
                )
            )
        )
        note = result.scalar_one_or_none()

        if not note:
            raise HTTPException(status_code=404, detail="Note not found")

        # Check if note has any submissions
        submission_result = await session.execute(
            select(Submission).where(Submission.note_id == note.note_id).limit(1)
        )
        has_submission = submission_result.scalar_one_or_none() is not None

        if has_submission:
            raise HTTPException(
                status_code=409,
                detail="Cannot delete note because it has already been submitted. Notes with submissions cannot be deleted to maintain submission history."
            )

        await session.delete(note)
        await session.commit()

        return {"message": "Note deleted successfully", "note_id": str(note.note_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Note editing endpoint
@router.patch("/notes/{note_id}", response_model=EditNoteResponse)
async def edit_note(
    note_id: str,
    request: EditNoteRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Edit a community note text and links"""
    try:
        # Get the note with fact_check and post relationships
        result = await session.execute(
            select(Note)
            .options(
                selectinload(Note.fact_check).selectinload(FactCheck.post)
            )
            .where(Note.note_id == uuid.UUID(note_id))
        )
        note = result.scalar_one_or_none()

        if not note:
            raise HTTPException(status_code=404, detail="Note not found")

        # If this is the first edit, save original values
        if not note.is_edited:
            note.original_text = note.text
            note.original_links = note.links
            note.is_edited = True

        # Update with new values
        note.text = request.text
        if request.links is not None:
            note.links = request.links

        # Rebuild submission_json for the platform
        platform = note.fact_check.post.platform

        if platform == "x":
            # Extract post_id from post_uid
            post_id = note.fact_check.post.post_uid.split("--")[1]

            # Build full text with links and More Details URL
            full_text = note.text
            if note.links:
                full_text += "\n\n" + "\n".join([link["url"] for link in note.links])
            full_text += f"\nMore Details: https://www.opennotenetwork.com/posts/{note.fact_check.post.post_uid}"

            # Preserve existing classification data if available
            if note.submission_json and "info" in note.submission_json:
                # Keep the AI-determined classification fields
                classification = note.submission_json["info"].get("classification", "misinformed_or_potentially_misleading")
                misleading_tags = note.submission_json["info"].get("misleading_tags", ["factual_error"])
                trustworthy_sources = note.submission_json["info"].get("trustworthy_sources", bool(note.links))
            else:
                # Defaults if no existing submission_json
                classification = "misinformed_or_potentially_misleading"
                misleading_tags = ["factual_error"]
                trustworthy_sources = bool(note.links)

            # Rebuild the submission_json
            note.submission_json = {
                "info": {
                    "text": full_text,
                    "classification": classification,
                    "misleading_tags": misleading_tags,
                    "trustworthy_sources": trustworthy_sources
                },
                "post_id": post_id,
                "test_mode": False
            }
        else:
            # For other platforms, throw error to force future implementation
            raise HTTPException(
                status_code=422,
                detail=f"Note editing not yet supported for platform '{platform}'. Only 'x' (X.com/Twitter) is currently supported."
            )

        # Trigger evaluation of the edited note BEFORE committing
        # Build full text for evaluation (already computed above)
        evaluation_result = await evaluate_note(
            note_text=full_text,
            post_id=post_id
        )

        # Update the note with evaluation result
        if evaluation_result:
            note.evaluation_json = evaluation_result
        await session.commit()
        await session.refresh(note)

        logger.info(
            "Note edited and evaluated",
            note_id=str(note.note_id),
            user=user.email,
            has_evaluation=bool(note.evaluation_json)
        )

        return EditNoteResponse(
            note_id=str(note.note_id),
            text=note.text,
            original_text=note.original_text,
            links=note.links,
            original_links=note.original_links,
            is_edited=note.is_edited,
            status=note.status
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error editing note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Submission endpoints
@router.post("/notes/{note_id}/submit", response_model=SubmitNoteResponse)
async def submit_note(
    note_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Submit a note to X.com Community Notes"""
    # Check if note already has a submission
    result = await session.execute(
        select(Submission)
        .where(Submission.note_id == uuid.UUID(note_id))
        .where(Submission.status != "submission_failed")
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Note already submitted with status: {existing.status}"
        )

    result = await submission.submit_note_to_x(
        note_id=uuid.UUID(note_id),
        session=session,
        submitted_by_id=user.user_id
    )

    # If submission failed, raise HTTPException with the error message
    if result["status"] == "submission_failed":
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to submit note")
        )

    return SubmitNoteResponse(**result)


@router.post("/submissions/update-statuses", response_model=UpdateStatusesResponse)
async def update_submission_statuses(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Update all submission statuses from X API"""
    result = await submission.update_submission_statuses(
        session=session
    )

    return UpdateStatusesResponse(**result)


@router.get("/submissions/status-summary", response_model=SubmissionsSummaryResponse)
async def get_submissions_summary(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Get summary statistics for submissions"""
    result = await submission.get_submissions_summary(session)

    return SubmissionsSummaryResponse(**result)


@router.get("/submissions/writing-limit", response_model=WritingLimitResponse)
async def get_writing_limit(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Calculate X.com daily writing limit based on submission history"""
    result = await submission.calculate_writing_limit(session)
    return WritingLimitResponse(**result)


@router.get("/submissions")
async def get_all_submissions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Get all submissions with details including evaluation outcomes"""
    from sqlalchemy import or_, func
    from app.models import Submission, Note, FactCheck, Post
    
    query = (
        select(Submission, Note, FactCheck, Post)
        .join(Note, Note.note_id == Submission.note_id)
        .join(FactCheck, FactCheck.fact_check_id == Note.fact_check_id)
        .join(Post, Post.post_uid == FactCheck.post_uid)
    )
    
    # Add search filter
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Post.text.ilike(search_term),
                Note.text.ilike(search_term),
                Submission.x_note_id.ilike(search_term)
            )
        )
    
    # Add status filter
    if status:
        query = query.where(Submission.status == status)
    
    # Order by submission date descending
    query = query.order_by(Submission.submitted_at.desc()).limit(limit).offset(offset)
    
    result = await session.execute(query)
    submissions_data = []
    
    for submission, note, fact_check, post in result.fetchall():
        # Extract evaluation outcomes from status_json if available
        evaluation_outcomes = []
        if submission.status_json:
            # Check for test_result in status_json
            if "test_result" in submission.status_json and submission.status_json["test_result"]:
                test_result = submission.status_json["test_result"]
                if isinstance(test_result, dict) and "evaluation_outcome" in test_result:
                    evaluation_outcomes = test_result["evaluation_outcome"]
                elif isinstance(test_result, list):
                    # Sometimes test_result might be the array directly
                    evaluation_outcomes = test_result
            # Also check if evaluation_outcome is at the top level
            elif "evaluation_outcome" in submission.status_json:
                evaluation_outcomes = submission.status_json["evaluation_outcome"]
        
        # Extract X status from status_json if available
        x_status = None
        if submission.status_json and isinstance(submission.status_json, dict):
            x_status = submission.status_json.get("status")

        submissions_data.append({
            "submission_id": str(submission.submission_id),
            "x_note_id": submission.x_note_id,
            "status": submission.status,
            "x_status": x_status,  # The detailed status from X API
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "status_updated_at": submission.status_updated_at.isoformat() if submission.status_updated_at else None,
            "note_text": note.text,
            "post_text": post.text[:200] + "..." if len(post.text) > 200 else post.text,
            "post_uid": post.post_uid,
            "fact_check_id": str(fact_check.fact_check_id),
            "platform_post_id": post.platform_post_id,
            "evaluation_outcomes": evaluation_outcomes
        })
    
    # Get total count
    count_query = (
        select(func.count(Submission.submission_id))
        .select_from(Submission)
    )
    
    if search:
        count_query = (
            count_query
            .join(Note, Note.note_id == Submission.note_id)
            .join(FactCheck, FactCheck.fact_check_id == Note.fact_check_id)
            .join(Post, Post.post_uid == FactCheck.post_uid)
            .where(
                or_(
                    Post.text.ilike(search_term),
                    Note.text.ilike(search_term),
                    Submission.x_note_id.ilike(search_term)
                )
            )
        )
    
    if status:
        count_query = count_query.where(Submission.status == status)
    
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0
    
    return {
        "submissions": submissions_data,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/submission-queue", response_model=SubmissionQueueResponse)
async def get_submission_queue(
    min_score: float = Query(-0.5, description="Minimum claim_opinion_score"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Get posts ready for submission with notes above the score threshold"""
    from sqlalchemy import case, cast, Float, distinct
    from sqlalchemy.sql import text

    # Subquery to get the best score for each post
    best_score_subquery = (
        select(
            FactCheck.post_uid,
            func.max(
                cast(
                    Note.evaluation_json['data']['claim_opinion_score'].astext,
                    Float
                )
            ).label('best_score'),
            func.count(Note.note_id).label('note_count')
        )
        .join(Note, Note.fact_check_id == FactCheck.fact_check_id)
        .where(
            and_(
                Note.status == 'completed',
                Note.evaluation_json['data']['claim_opinion_score'].astext.isnot(None),
                cast(
                    Note.evaluation_json['data']['claim_opinion_score'].astext,
                    Float
                ) > min_score
            )
        )
        .group_by(FactCheck.post_uid)
        .subquery()
    )

    # Main query to get posts that have no submissions yet
    query = (
        select(
            Post.post_uid,
            Post.text,
            Post.created_at,
            best_score_subquery.c.best_score,
            best_score_subquery.c.note_count
        )
        .join(best_score_subquery, Post.post_uid == best_score_subquery.c.post_uid)
        .outerjoin(
            FactCheck,
            FactCheck.post_uid == Post.post_uid
        )
        .outerjoin(
            Note,
            Note.fact_check_id == FactCheck.fact_check_id
        )
        .outerjoin(
            Submission,
            Submission.note_id == Note.note_id
        )
        .where(Submission.submission_id.is_(None))
        .group_by(
            Post.post_uid,
            Post.text,
            Post.created_at,
            best_score_subquery.c.best_score,
            best_score_subquery.c.note_count
        )
        .order_by(Post.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(query)
    rows = result.all()

    items = [
        SubmissionQueueItem(
            post_uid=row[0],
            post_text=row[1],
            created_at=row[2],
            best_score=float(row[3]),
            note_count=int(row[4])
        )
        for row in rows
    ]

    # Count total posts in queue
    count_query = (
        select(func.count(distinct(Post.post_uid)))
        .select_from(Post)
        .join(best_score_subquery, Post.post_uid == best_score_subquery.c.post_uid)
        .outerjoin(
            FactCheck,
            FactCheck.post_uid == Post.post_uid
        )
        .outerjoin(
            Note,
            Note.fact_check_id == FactCheck.fact_check_id
        )
        .outerjoin(
            Submission,
            Submission.note_id == Note.note_id
        )
        .where(Submission.submission_id.is_(None))
    )

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    return SubmissionQueueResponse(items=items, total=total)


# Batch fact checking endpoints
batch_fact_check_jobs = {}  # Store job status in memory

@router.get("/posts-date-range/fact-check-eligible-count", response_model=FactCheckEligibleCountResponse)
async def count_fact_check_eligible(
    start_date: str,
    end_date: str,
    fact_checker_slugs: Optional[List[str]] = Query(None),
    force: bool = False,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Count posts in date range that are eligible for fact checking"""
    try:
        # Parse dates
        start_dt, end_dt = parse_iso_dates(start_date, end_date)
        
        # Count eligible posts
        count = await fact_checking.count_fact_check_eligible_posts(
            start_date=start_dt,
            end_date=end_dt,
            fact_checker_slugs=fact_checker_slugs,
            force=force
        )
        
        return FactCheckEligibleCountResponse(
            post_count=count,
            date_range={"start": start_dt, "end": end_dt},
            fact_checker_slugs=fact_checker_slugs
        )
    except Exception as e:
        logger.error("Failed to count fact check eligible posts", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-fact-check", response_model=BatchFactCheckResponse)
async def start_batch_fact_check(
    start_date: str = Query(...),
    end_date: str = Query(...),
    fact_checker_slugs: Optional[List[str]] = Query(None),
    force: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Start a batch fact checking job for posts in date range"""
    import asyncio
    from datetime import datetime as dt
    
    job_id = str(uuid.uuid4())
    
    try:
        # Parse dates
        start_dt, end_dt = parse_iso_dates(start_date, end_date)
        
        # Count posts first
        total_posts = await fact_checking.count_fact_check_eligible_posts(
            start_date=start_dt,
            end_date=end_dt,
            fact_checker_slugs=fact_checker_slugs,
            force=force
        )
        
        # Initialize job status
        batch_fact_check_jobs[job_id] = BatchFactCheckJobStatus(
            job_id=job_id,
            status="running",
            total_posts=total_posts,
            processed=0,
            fact_checks_triggered=0,
            skipped=0,
            errors=[],
            progress_percentage=0.0,
            started_at=dt.utcnow(),
            completed_at=None
        )
        
        async def run_batch_job():
            try:
                # Update status to indicate we're processing
                batch_fact_check_jobs[job_id].status = "running"
                
                # Run the batch fact checking
                result = await fact_checking.run_batch_fact_checks(
                    start_date=start_dt,
                    end_date=end_dt,
                    fact_checker_slugs=fact_checker_slugs,
                    force=force,
                    job_id=job_id
                )
                
                # Update job with results
                batch_fact_check_jobs[job_id] = BatchFactCheckJobStatus(
                    job_id=job_id,
                    status="completed",
                    total_posts=result["total_posts"],
                    processed=result["processed"],
                    fact_checks_triggered=result["fact_checks_triggered"],
                    skipped=result["skipped"],
                    errors=result.get("errors", []),
                    progress_percentage=100.0,
                    started_at=batch_fact_check_jobs[job_id].started_at,
                    completed_at=dt.utcnow()
                )
            except Exception as e:
                logger.error("Batch fact check job failed", job_id=job_id, error=str(e))
                batch_fact_check_jobs[job_id] = BatchFactCheckJobStatus(
                    job_id=job_id,
                    status="failed",
                    total_posts=batch_fact_check_jobs[job_id].total_posts,
                    processed=batch_fact_check_jobs[job_id].processed,
                    fact_checks_triggered=batch_fact_check_jobs[job_id].fact_checks_triggered,
                    skipped=batch_fact_check_jobs[job_id].skipped,
                    errors=[str(e)],
                    progress_percentage=batch_fact_check_jobs[job_id].progress_percentage,
                    started_at=batch_fact_check_jobs[job_id].started_at,
                    completed_at=dt.utcnow()
                )
        
        # Start the job in the background
        asyncio.create_task(run_batch_job())
        
        logger.info("Started batch fact check job", job_id=job_id, total_posts=total_posts)
        
        return BatchFactCheckResponse(
            job_id=job_id,
            status="started",
            message=f"Batch fact checking started for {total_posts} posts",
            total_posts=total_posts
        )
        
    except Exception as e:
        logger.error("Failed to start batch fact check", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch-fact-check/{job_id}/status", response_model=BatchFactCheckJobStatus)
async def get_batch_fact_check_status(
    job_id: str,
    user: User = Depends(require_admin)
):
    """Get the status of a batch fact checking job"""
    if job_id not in batch_fact_check_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_status = batch_fact_check_jobs[job_id]
    
    # Update progress percentage for running jobs
    if job_status.status == "running" and job_status.total_posts > 0:
        job_status.progress_percentage = (job_status.processed / job_status.total_posts) * 100
    
    return job_status
