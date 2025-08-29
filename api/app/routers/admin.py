from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from typing import Optional, List
import structlog
import uuid

from app.database import get_session
from app.models import Post, DraftNote, Submission, Topic, PostTopic, User, Classifier, Classification
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
from app.auth import get_current_admin_user

logger = structlog.get_logger()

router = APIRouter()


# Middleware for admin authentication
async def verify_admin_auth(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> User:
    """Verify admin authentication"""
    try:
        user = await get_current_admin_user(authorization, session)
        return user
    except Exception as e:
        logger.error("Admin authentication failed", error=str(e))
        raise HTTPException(status_code=401, detail="Unauthorized")


# Ingestion endpoints
@router.post("/ingest", response_model=IngestResponse)
async def trigger_ingestion(
    batch_size: int = 50,  # Posts per API request
    max_total_posts: int = 500,  # Maximum total posts to process  
    duplicate_threshold: float = 0.7,  # Stop if this ratio are duplicates
    auto_classify: bool = True,  # Automatically classify new posts
    classifier_slugs: Optional[List[str]] = Query(None),  # Specific classifiers to run
    x_ingest_secret: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Trigger ingestion of Community Note requests from X.com"""
    # Verify ingest secret for automated triggers
    from app.config import settings
    if x_ingest_secret != settings.ingest_secret:
        raise HTTPException(status_code=401, detail="Invalid ingest secret")
    
    try:
        result = await ingestion.run_ingestion(
            session, 
            batch_size=batch_size,
            max_total_posts=max_total_posts,
            duplicate_threshold=duplicate_threshold,
            auto_classify=auto_classify,
            classifier_slugs=classifier_slugs
        )
        return IngestResponse(
            added=result["added"],
            skipped=result["skipped"],
            classified=result.get("classified", 0),
            errors=result.get("errors", []),
            classification_errors=result.get("classification_errors", [])
        )
    except Exception as e:
        logger.error("Ingestion failed", error=str(e))
        raise HTTPException(status_code=500, detail="Ingestion failed")


@router.post("/test-x-auth")
async def test_x_auth():
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
    user: User = Depends(verify_admin_auth),
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
    user: User = Depends(verify_admin_auth),
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
    user: User = Depends(verify_admin_auth),
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
    user: User = Depends(verify_admin_auth),
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
    user: User = Depends(verify_admin_auth),
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
    user: User = Depends(verify_admin_auth),
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
    user: User = Depends(verify_admin_auth),
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
    x_reconcile_secret: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Reconcile submission outcomes from X.com"""
    # Verify reconcile secret for automated triggers
    from app.config import settings
    if x_reconcile_secret != settings.reconcile_secret:
        raise HTTPException(status_code=401, detail="Invalid reconcile secret")
    
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


# Admin data endpoints
@router.get("/posts/{post_uid}", response_model=PostDetailResponse)
async def get_post_detail(
    post_uid: str,
    user: User = Depends(verify_admin_auth),
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


# Classifier management endpoints
@router.get("/classifiers", response_model=ClassifierListResponse)
async def list_classifiers(
    group_name: Optional[str] = None,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_session)
):
    """List all classifiers with optional filtering"""
    try:
        query = select(Classifier)
        
        if group_name is not None:
            query = query.where(Classifier.group_name == group_name)
        if is_active is not None:
            query = query.where(Classifier.is_active == is_active)
        
        query = query.order_by(Classifier.group_name, Classifier.slug)
        
        result = await session.execute(query)
        classifiers = result.scalars().all()
        
        # Count classifications for each classifier
        classifier_responses = []
        for clf in classifiers:
            count_result = await session.execute(
                select(func.count(Classification.classification_id))
                .where(Classification.classifier_slug == clf.slug)
            )
            count = count_result.scalar() or 0
            
            classifier_responses.append(ClassifierResponse(
                classifier_id=str(clf.classifier_id),
                slug=clf.slug,
                display_name=clf.display_name,
                description=clf.description,
                group_name=clf.group_name,
                is_active=clf.is_active,
                output_schema=clf.output_schema,
                config=clf.config or {},
                created_at=clf.created_at,
                updated_at=clf.updated_at,
                classification_count=count
            ))
        
        return ClassifierListResponse(
            classifiers=classifier_responses,
            total=len(classifier_responses)
        )
        
    except Exception as e:
        logger.error("Failed to list classifiers", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list classifiers")


@router.get("/classifiers/{slug}", response_model=ClassifierResponse)
async def get_classifier(
    slug: str,
    session: AsyncSession = Depends(get_session)
):
    """Get a specific classifier by slug"""
    try:
        result = await session.execute(
            select(Classifier).where(Classifier.slug == slug)
        )
        classifier = result.scalar_one_or_none()
        
        if not classifier:
            raise HTTPException(status_code=404, detail="Classifier not found")
        
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
        logger.error("Failed to get classifier", slug=slug, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get classifier")


@router.post("/classifiers", response_model=ClassifierResponse)
async def create_classifier(
    request: ClassifierCreate,
    session: AsyncSession = Depends(get_session)
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
    session: AsyncSession = Depends(get_session)
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
    session: AsyncSession = Depends(get_session)
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
    session: AsyncSession = Depends(get_session)
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
    session: AsyncSession = Depends(get_session)
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
    session: AsyncSession = Depends(get_session)
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
    session: AsyncSession = Depends(get_session)
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