from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from typing import Optional, List
import structlog
import uuid

from app.database import get_session
from app.models import Post, DraftNote, Submission, Topic, PostTopic, User, Classifier, Classification, FactChecker, FactCheck
from app.schemas.admin import (
    IngestResponse,
    GenerateDraftRequest, GenerateDraftResponse,
    EditDraftRequest, SubmissionResponse, ReconcileResponse,
    PostDetailResponse, AdminPostResponse,
    ClassifierCreate, ClassifierUpdate, ClassifierResponse, ClassifierListResponse,
    ClassificationCreate, ClassificationResponse
)
from app.services import ingestion, notegen, submission
from app.services import classification
from app.services import fact_checking
from datetime import datetime

def parse_iso_dates(start_date: str, end_date: str) -> tuple[datetime, datetime]:
    """Parse ISO date strings, handling 'Z' timezone indicator"""
    start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    return start, end
from app.auth import require_admin, get_current_user

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
    classifier_slugs: Optional[List[str]] = Query(None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
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
        try:
            # Update status to indicate we're fetching
            ingestion_jobs[job_id]["message"] = "Fetching posts from X.com..."
            
            result = await ingestion.run_ingestion(
                session,
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
    from app.services.ingestion import XAPIClient
    from app.config import settings
    import asyncio
    
    # Debug: Show what credentials we're actually using (partially masked)
    debug_info = {
        "api_key_preview": settings.x_api_key[:10] + "..." if settings.x_api_key else "MISSING",
        "api_secret_preview": settings.x_api_key_secret[:10] + "..." if settings.x_api_key_secret else "MISSING",
        "token_preview": settings.x_access_token[:10] + "..." if settings.x_access_token else "MISSING",
        "token_secret_preview": settings.x_access_token_secret[:10] + "..." if settings.x_access_token_secret else "MISSING"
    }
    
    try:
        # Test with xurl - the method that actually works
        import subprocess
        import json
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(["xurl", "/2/users/me"], check=True, text=True, capture_output=True)
        )
        
        data = json.loads(result.stdout)
        return {"status": "success", "user": data, "debug": debug_info}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "error": f"xurl failed: {e.stderr}", "debug": debug_info}
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


# Draft generation endpoints
@router.post("/posts/{post_uid}/drafts", response_model=GenerateDraftResponse)
async def generate_draft(
    post_uid: str,
    request: GenerateDraftRequest,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """Generate a new draft note"""
    try:
        result = await notegen.generate(post_uid, session, topic_slug=request.topic_slug)
        return GenerateDraftResponse(
            draft_id=result["draft_id"],
            post_uid=post_uid,
            full_body=result["full_body"],
            concise_body=result["concise_body"],
            citations=result.get("citations", []),
            generator_version=result["generator_version"]
        )
    except Exception as e:
        logger.error("Draft generation failed", post_uid=post_uid, error=str(e))
        raise HTTPException(status_code=500, detail="Draft generation failed")


@router.post("/drafts/{draft_id}:regenerate", response_model=GenerateDraftResponse)
async def regenerate_draft(
    draft_id: str,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """Regenerate a draft note"""
    try:
        # Get existing draft
        result = await session.execute(
            select(DraftNote).where(DraftNote.draft_id == uuid.UUID(draft_id))
        )
        existing_draft = result.scalar_one_or_none()
        if not existing_draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        result = await notegen.regenerate(draft_id, session)
        return GenerateDraftResponse(
            draft_id=result["draft_id"],
            post_uid=result["post_uid"],
            full_body=result["full_body"],
            concise_body=result["concise_body"],
            citations=result.get("citations", []),
            generator_version=result["generator_version"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Draft regeneration failed", draft_id=draft_id, error=str(e))
        raise HTTPException(status_code=500, detail="Draft regeneration failed")


@router.patch("/drafts/{draft_id}")
async def edit_draft(
    draft_id: str,
    request: EditDraftRequest,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """Edit draft content"""
    try:
        # Update draft
        await session.execute(
            update(DraftNote)
            .where(DraftNote.draft_id == uuid.UUID(draft_id))
            .values(
                full_body=request.full_body,
                concise_body=request.concise_body,
                citations=request.citations,
                edited_by=user.user_id,
                edited_at=func.now()
            )
        )
        await session.commit()
        
        return {"message": "Draft updated successfully"}
        
    except Exception as e:
        logger.error("Failed to edit draft", draft_id=draft_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to edit draft")


@router.post("/drafts/{draft_id}:approve")
async def approve_draft(
    draft_id: str,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """Approve a draft for submission"""
    try:
        # Get draft to validate
        result = await session.execute(
            select(DraftNote).where(DraftNote.draft_id == uuid.UUID(draft_id))
        )
        draft = result.scalar_one_or_none()
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        # Validate constraints
        from app.services.validation import validate_concise_note
        is_valid, errors = await validate_concise_note(draft.concise_body)
        if not is_valid:
            raise HTTPException(status_code=422, detail={"validation_errors": errors})
        
        # Update status
        await session.execute(
            update(DraftNote)
            .where(DraftNote.draft_id == uuid.UUID(draft_id))
            .values(draft_status="approved")
        )
        await session.commit()
        
        return {"message": "Draft approved successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to approve draft", draft_id=draft_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to approve draft")


# Submission endpoints
@router.post("/drafts/{draft_id}:submit", response_model=SubmissionResponse)
async def submit_draft(
    draft_id: str,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """Submit approved draft to X.com"""
    try:
        result = await submission.submit(draft_id, user.user_id, session)
        return SubmissionResponse(
            submission_id=result["submission_id"],
            x_note_id=result.get("x_note_id"),
            status=result["status"]
        )
    except Exception as e:
        logger.error("Submission failed", draft_id=draft_id, error=str(e))
        raise HTTPException(status_code=500, detail="Submission failed")


# Reconciliation endpoints
@router.post("/submissions/reconcile", response_model=ReconcileResponse)
async def reconcile_submissions(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Reconcile submission outcomes from X.com"""
    
    try:
        result = await submission.reconcile(session)
        return ReconcileResponse(
            checked=result["checked"],
            updated=result["updated"],
            unchanged=result["unchanged"]
        )
    except Exception as e:
        logger.error("Reconciliation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Reconciliation failed")


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
        
        # Get drafts
        draft_query = (
            select(DraftNote)
            .where(DraftNote.post_uid == post_uid)
            .order_by(DraftNote.generated_at.desc())
        )
        draft_result = await session.execute(draft_query)
        drafts = draft_result.scalars().all()
        
        # Get submissions
        submission_query = (
            select(Submission)
            .where(Submission.post_uid == post_uid)
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
            drafts=[
                {
                    "draft_id": str(draft.draft_id),
                    "full_body": draft.full_body,
                    "concise_body": draft.concise_body,
                    "citations": draft.citations,
                    "status": draft.draft_status,
                    "generated_at": draft.generated_at,
                    "generator_version": draft.generator_version
                }
                for draft in drafts
            ],
            submissions=[
                {
                    "submission_id": str(submission.submission_id),
                    "x_note_id": submission.x_note_id,
                    "status": submission.submission_status,
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
@router.get("/posts/{post_uid}/classifications", response_model=List[ClassificationResponse])
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
    classifier_slugs: Optional[List[str]] = Query(None),
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
            session=session,
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
    post_uids: List[str],
    classifier_slugs: Optional[List[str]] = Query(None),
    force: bool = Query(True),
    parallel: bool = Query(True),
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
        parallel: Whether to run in parallel (default: True)
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
            session=session,
            classifier_slugs=classifier_slugs,
            parallel=parallel
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
    classifier_slugs: Optional[List[str]] = Query(None),
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


# Fact Checker endpoints
@router.get("/fact-checkers")
async def list_fact_checkers(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """List all available fact checkers"""
    try:
        fact_checkers = await fact_checking.list_available_fact_checkers(session)
        return {"fact_checkers": fact_checkers}
    except Exception as e:
        logger.error("Failed to list fact checkers", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list fact checkers")


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
            session=session,
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


@router.get("/posts/{post_uid}/fact-checks")
async def get_post_fact_checks(
    post_uid: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Get all fact checks for a post"""
    try:
        fact_checks = await fact_checking.get_fact_checks_for_post(post_uid, session)
        return {"fact_checks": fact_checks}
    except Exception as e:
        logger.error("Failed to get fact checks", post_uid=post_uid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get fact checks")


@router.get("/fact-checks/{fact_check_id}/status")
async def get_fact_check_status(
    fact_check_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin)
):
    """Get the status of a fact check job"""
    try:
        status = await fact_checking.get_fact_check_status(fact_check_id, session)
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
                    FactCheck.fact_checker_id == fact_checker.id
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