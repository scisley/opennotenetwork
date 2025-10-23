from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
import structlog
import json

from app.database import get_session
from app.schemas.public import PostListResponse
from app.services.posts import get_posts_with_filters, get_single_post_with_metadata

logger = structlog.get_logger()

router = APIRouter()


@router.get("/posts", response_model=PostListResponse)
async def get_public_posts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, max_length=200),
    classification_filters: Optional[str] = Query(None, description="JSON-encoded classification filters"),
    has_fact_check: Optional[bool] = Query(None, description="Filter posts with fact checks"),
    has_note: Optional[bool] = Query(None, description="Filter posts with submitted notes"),
    fact_check_status: Optional[str] = Query(None, description="Filter by fact check status: no_fact_check, fact_checked, note_written, note_submitted"),
    note_status: Optional[str] = Query(None, description="Filter by note status: not_submitted, submitted, rated_helpful, rated_unhelpful, needs_more_ratings"),
    created_after: Optional[datetime] = Query(None, description="Filter posts created after this datetime"),
    created_before: Optional[datetime] = Query(None, description="Filter posts created before this datetime"),
    include_raw_json: bool = Query(False, description="Include raw JSON data (needed for media display)"),
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

    Fact check status options:
    - no_fact_check: Posts without any fact checks
    - fact_checked: Posts with completed fact checks but no notes
    - note_written: Posts with notes but not submitted
    - note_submitted: Posts with submitted notes

    Note status options:
    - not_submitted: Notes that exist but were not submitted
    - submitted: Notes that were submitted (any status)
    - rated_helpful: Notes rated helpful by the community (status: displayed)
    - rated_unhelpful: Notes rated unhelpful by the community (status: not_displayed)
    - needs_more_ratings: Notes that need more ratings (status: submitted)
    """
    try:
        # Parse classification filters if provided
        filters_dict = {}
        if classification_filters:
            try:
                filters_dict = json.loads(classification_filters)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid classification_filters JSON")
        
        # Get posts using service function
        posts, total = await get_posts_with_filters(
            session=session,
            limit=limit,
            offset=offset,
            search=search,
            filters_dict=filters_dict,
            has_fact_check=has_fact_check,
            has_note=has_note,
            fact_check_status=fact_check_status,
            note_status=note_status,
            created_after=created_after,
            created_before=created_before,
            include_raw_json=include_raw_json
        )
        
        return PostListResponse(
            posts=posts,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get public posts", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/posts/{post_uid}")
async def get_post_by_uid(
    post_uid: str,
    session: AsyncSession = Depends(get_session)
):
    """Get a specific post with any associated classifications"""
    try:
        post = await get_single_post_with_metadata(session, post_uid)
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        return post
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get post by uid", post_uid=post_uid, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")