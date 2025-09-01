from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_, exists, text
from typing import List, Optional, Dict, Any
import structlog
import json

from app.database import get_session
from app.models import Post, DraftNote, Submission, Topic, PostTopic, Classification, Classifier
from app.schemas.public import (
    NotePublicResponse, NoteListResponse, 
    PostPublicResponse, PostListResponse,
    ClassificationPublicResponse, PostWithClassificationsResponse
)

logger = structlog.get_logger()

router = APIRouter()


@router.get("/notes", response_model=NoteListResponse)
async def get_public_notes(
    status: Optional[str] = Query(None, regex="^(submitted|accepted)$"),
    topic_slug: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session)
):
    """Get list of submitted and accepted notes"""
    try:
        # Base query for notes with submissions
        query = (
            select(DraftNote, Post, Submission, Topic)
            .join(Post, DraftNote.post_uid == Post.post_uid)
            .join(Submission, DraftNote.draft_id == Submission.draft_id)
            .outerjoin(Topic, DraftNote.topic_id == Topic.topic_id)
            .where(DraftNote.draft_status == "submitted")
        )
        
        # Filter by submission status
        if status:
            if status == "submitted":
                query = query.where(Submission.submission_status.in_(["submitted", "unknown"]))
            elif status == "accepted":
                query = query.where(Submission.submission_status == "accepted")
        else:
            # Default: show submitted and accepted only
            query = query.where(Submission.submission_status.in_(["submitted", "accepted", "unknown"]))
        
        # Filter by topic
        if topic_slug:
            query = query.where(Topic.slug == topic_slug)
        
        # Add ordering and pagination
        query = query.order_by(DraftNote.generated_at.desc()).limit(limit).offset(offset)
        
        result = await session.execute(query)
        rows = result.fetchall()
        
        notes = []
        for draft_note, post, submission, topic in rows:
            notes.append(NotePublicResponse(
                post_uid=post.post_uid,
                post_text=post.text,
                author_handle=post.author_handle,
                concise_body=draft_note.concise_body,
                citations=draft_note.citations or [],
                topic_slug=topic.slug if topic else None,
                topic_display_name=topic.display_name if topic else None,
                submission_status=submission.submission_status,
                submitted_at=submission.submitted_at,
                generated_at=draft_note.generated_at
            ))
        
        return NoteListResponse(
            notes=notes,
            total=len(notes),  # TODO: implement proper count query
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error("Failed to get public notes", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/notes/{post_uid}", response_model=NotePublicResponse)
async def get_note_by_post(
    post_uid: str,
    session: AsyncSession = Depends(get_session)
):
    """Get submitted/accepted note for a specific post"""
    try:
        # Query for the note
        query = (
            select(DraftNote, Post, Submission, Topic)
            .join(Post, DraftNote.post_uid == Post.post_uid)
            .join(Submission, DraftNote.draft_id == Submission.draft_id)
            .outerjoin(Topic, DraftNote.topic_id == Topic.topic_id)
            .where(
                and_(
                    Post.post_uid == post_uid,
                    DraftNote.draft_status == "submitted",
                    Submission.submission_status.in_(["submitted", "accepted", "unknown"])
                )
            )
            .order_by(DraftNote.generated_at.desc())
        )
        
        result = await session.execute(query)
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="Note not found")
        
        draft_note, post, submission, topic = row
        
        return NotePublicResponse(
            post_uid=post.post_uid,
            post_text=post.text,
            author_handle=post.author_handle,
            full_body=draft_note.full_body,
            concise_body=draft_note.concise_body,
            citations=draft_note.citations or [],
            topic_slug=topic.slug if topic else None,
            topic_display_name=topic.display_name if topic else None,
            submission_status=submission.submission_status,
            submitted_at=submission.submitted_at,
            generated_at=draft_note.generated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get note by post", post_uid=post_uid, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/posts", response_model=PostListResponse)
async def get_public_posts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, max_length=200),
    classification_filters: Optional[str] = Query(None, description="JSON-encoded classification filters"),
    session: AsyncSession = Depends(get_session)
):
    """
    Get list of all posts for browsing (most recent first).
    
    Classification filters format:
    {
        "classifier_slug": {
            "has_classification": true,  # Filter for posts that have this classification
            "values": ["value1"],  # For single/multi select
            "hierarchy": {  # For hierarchical classifiers
                "level1": "value",
                "level2": "value"
            }
        }
    }
    """
    try:
        # Parse classification filters if provided
        filters_dict = {}
        if classification_filters:
            try:
                filters_dict = json.loads(classification_filters)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid classification_filters JSON")
        
        # Base query for all posts with optional note information
        query = (
            select(Post, DraftNote, Submission, Topic)
            .outerjoin(DraftNote, and_(
                Post.post_uid == DraftNote.post_uid,
                DraftNote.draft_status == "submitted"
            ))
            .outerjoin(Submission, DraftNote.draft_id == Submission.draft_id)
            .outerjoin(Topic, DraftNote.topic_id == Topic.topic_id)
        )
        
        # Add classification filters
        for classifier_slug, filter_config in filters_dict.items():
            # Create subquery for this classifier
            classification_exists = exists().where(
                and_(
                    Classification.post_uid == Post.post_uid,
                    Classification.classifier_slug == classifier_slug
                )
            )
            
            # Check if we want posts with this classification
            if filter_config.get("has_classification"):
                query = query.where(classification_exists)
            
            # Filter by specific values (for single/multi select)
            if filter_config.get("values"):
                values = filter_config["values"]
                if isinstance(values, list) and values:
                    # Create conditions for matching values
                    value_conditions = []
                    for value in values:
                        # For single select: classification_data->>'value' = value
                        # For multi select: classification_data->'values' @> [{"value": value}]
                        value_conditions.append(
                            exists().where(
                                and_(
                                    Classification.post_uid == Post.post_uid,
                                    Classification.classifier_slug == classifier_slug,
                                    or_(
                                        Classification.classification_data["value"].astext == value,
                                        # For multi-select, check if the values array contains an object with this value
                                        Classification.classification_data["values"].contains([{"value": value}])
                                    )
                                )
                            )
                        )
                    if value_conditions:
                        query = query.where(or_(*value_conditions))
            
            # Filter by hierarchy (for hierarchical classifiers)
            if filter_config.get("hierarchy"):
                hierarchy = filter_config["hierarchy"]
                hierarchy_conditions = []
                
                if hierarchy.get("level1"):
                    # Check if the levels array contains an object with level=1 and the specified value
                    hierarchy_conditions.append(
                        Classification.classification_data["levels"].contains([{"level": 1, "value": hierarchy["level1"]}])
                    )
                
                if hierarchy.get("level2"):
                    # Check if the levels array contains an object with level=2 and the specified value
                    hierarchy_conditions.append(
                        Classification.classification_data["levels"].contains([{"level": 2, "value": hierarchy["level2"]}])
                    )
                
                if hierarchy_conditions:
                    query = query.where(
                        exists().where(
                            and_(
                                Classification.post_uid == Post.post_uid,
                                Classification.classifier_slug == classifier_slug,
                                *hierarchy_conditions
                            )
                        )
                    )
        
        # Add search filter if provided
        if search:
            search_term = f"%{search.strip()}%"
            query = query.where(Post.text.ilike(search_term))
        
        # Add ordering and pagination
        query = query.order_by(Post.created_at.desc().nulls_last(), Post.ingested_at.desc()).limit(limit).offset(offset)
        
        result = await session.execute(query)
        rows = result.fetchall()
        
        # Get all post UIDs for classification lookup
        post_uids = [row[0].post_uid for row in rows]
        
        # Batch fetch classifications for all posts
        classifications_by_post = {}
        if post_uids:
            classification_query = (
                select(Classification, Classifier)
                .join(Classifier, Classification.classifier_slug == Classifier.slug)
                .where(Classification.post_uid.in_(post_uids))
                .order_by(Classification.post_uid, Classifier.group_name, Classifier.slug)
            )
            classification_result = await session.execute(classification_query)
            
            for classification, classifier in classification_result.fetchall():
                if classification.post_uid not in classifications_by_post:
                    classifications_by_post[classification.post_uid] = []
                
                classifications_by_post[classification.post_uid].append(
                    ClassificationPublicResponse(
                        classifier_slug=classifier.slug,
                        classifier_display_name=classifier.display_name,
                        classifier_group=classifier.group_name,
                        classification_type=classifier.output_schema.get("type", "unknown"),
                        classification_data=classification.classification_data,
                        output_schema=classifier.output_schema,
                        created_at=classification.created_at,
                        updated_at=classification.updated_at
                    )
                )
        
        posts = []
        for post, draft_note, submission, topic in rows:
            # Check if post has a submitted note
            has_note = draft_note is not None and submission is not None
            submission_status = submission.submission_status if submission else None
            
            # Get classifications for this post
            post_classifications = classifications_by_post.get(post.post_uid, [])
            
            posts.append(PostWithClassificationsResponse(
                post_uid=post.post_uid,
                platform=post.platform,
                platform_post_id=post.platform_post_id,
                author_handle=post.author_handle,
                text=post.text,
                created_at=post.created_at,
                ingested_at=post.ingested_at,
                has_note=has_note,
                submission_status=submission_status,
                topic_slug=topic.slug if topic else None,
                topic_display_name=topic.display_name if topic else None,
                generated_at=draft_note.generated_at if draft_note else None,
                classifications=post_classifications
            ))
        
        # Get total count for pagination (efficient count query with same filters)
        count_query = select(func.count(Post.post_uid))
        
        # Apply same classification filters to count query
        for classifier_slug, filter_config in filters_dict.items():
            classification_exists = exists().where(
                and_(
                    Classification.post_uid == Post.post_uid,
                    Classification.classifier_slug == classifier_slug
                )
            )
            
            if filter_config.get("has_classification"):
                count_query = count_query.where(classification_exists)
            
            if filter_config.get("values"):
                values = filter_config["values"]
                if isinstance(values, list) and values:
                    value_conditions = []
                    for value in values:
                        value_conditions.append(
                            exists().where(
                                and_(
                                    Classification.post_uid == Post.post_uid,
                                    Classification.classifier_slug == classifier_slug,
                                    or_(
                                        Classification.classification_data["value"].astext == value,
                                        # For multi-select, check if the values array contains an object with this value
                                        Classification.classification_data["values"].contains([{"value": value}])
                                    )
                                )
                            )
                        )
                    if value_conditions:
                        count_query = count_query.where(or_(*value_conditions))
            
            if filter_config.get("hierarchy"):
                hierarchy = filter_config["hierarchy"]
                hierarchy_conditions = []
                
                if hierarchy.get("level1"):
                    # Check if the levels array contains an object with level=1 and the specified value
                    hierarchy_conditions.append(
                        Classification.classification_data["levels"].contains([{"level": 1, "value": hierarchy["level1"]}])
                    )
                
                if hierarchy.get("level2"):
                    # Check if the levels array contains an object with level=2 and the specified value
                    hierarchy_conditions.append(
                        Classification.classification_data["levels"].contains([{"level": 2, "value": hierarchy["level2"]}])
                    )
                
                if hierarchy_conditions:
                    count_query = count_query.where(
                        exists().where(
                            and_(
                                Classification.post_uid == Post.post_uid,
                                Classification.classifier_slug == classifier_slug,
                                *hierarchy_conditions
                            )
                        )
                    )
        
        if search:
            search_term = f"%{search.strip()}%"
            count_query = count_query.where(Post.text.ilike(search_term))
        
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0
        
        return PostListResponse(
            posts=posts,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error("Failed to get public posts", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/posts/{post_uid}", response_model=PostWithClassificationsResponse)
async def get_post_by_uid(
    post_uid: str,
    session: AsyncSession = Depends(get_session)
):
    """Get a specific post with any associated note information and classifications"""
    try:
        # Query for the post with optional note information
        query = (
            select(Post, DraftNote, Submission, Topic)
            .outerjoin(DraftNote, and_(
                Post.post_uid == DraftNote.post_uid,
                DraftNote.draft_status == "submitted"
            ))
            .outerjoin(Submission, DraftNote.draft_id == Submission.draft_id)
            .outerjoin(Topic, DraftNote.topic_id == Topic.topic_id)
            .where(Post.post_uid == post_uid)
        )
        
        result = await session.execute(query)
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="Post not found")
        
        post, draft_note, submission, topic = row
        
        # Check if post has a submitted note
        has_note = draft_note is not None and submission is not None
        submission_status = submission.submission_status if submission else None
        
        # Get classifications for this post
        classification_query = (
            select(Classification, Classifier)
            .join(Classifier, Classification.classifier_slug == Classifier.slug)
            .where(Classification.post_uid == post_uid)
            .order_by(Classifier.group_name, Classifier.slug)
        )
        
        classification_result = await session.execute(classification_query)
        classifications = []
        
        for classification, classifier in classification_result.fetchall():
            classifications.append(ClassificationPublicResponse(
                classifier_slug=classifier.slug,
                classifier_display_name=classifier.display_name,
                classifier_group=classifier.group_name,
                classification_type=classifier.output_schema.get("type", "unknown"),
                classification_data=classification.classification_data,
                output_schema=classifier.output_schema,
                created_at=classification.created_at,
                updated_at=classification.updated_at
            ))
        
        return PostWithClassificationsResponse(
            post_uid=post.post_uid,
            platform=post.platform,
            platform_post_id=post.platform_post_id,
            author_handle=post.author_handle,
            text=post.text,
            created_at=post.created_at,
            ingested_at=post.ingested_at,
            has_note=has_note,
            submission_status=submission_status,
            topic_slug=topic.slug if topic else None,
            topic_display_name=topic.display_name if topic else None,
            generated_at=draft_note.generated_at if draft_note else None,
            # Include note content if available
            full_body=draft_note.full_body if draft_note else None,
            concise_body=draft_note.concise_body if draft_note else None,
            citations=draft_note.citations if draft_note else None,
            # Include raw JSON for debugging
            raw_json=post.raw_json,
            # Include classifications
            classifications=classifications
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get post by uid", post_uid=post_uid, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")