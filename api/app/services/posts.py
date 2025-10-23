"""
Service layer functions for posts endpoints.
Handles complex query building and data fetching logic.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, and_, func, or_, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from app.models import Post, Submission, Note, FactCheck, Classification, Classifier
from app.schemas.public import ClassificationPublicResponse, PostWithClassificationsResponse


async def apply_classification_filters(
    query: Query,
    filters_dict: Dict[str, Any]
) -> Query:
    """
    Apply classification filters to a query.
    This function modifies the query to filter posts based on classification criteria.
    """
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
                hierarchy_conditions.append(
                    Classification.classification_data["levels"].contains([{"level": 1, "value": hierarchy["level1"]}])
                )
            
            if hierarchy.get("level2"):
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
    
    return query


def apply_status_filters(
    query: Query,
    has_fact_check: Optional[bool] = None,
    has_note: Optional[bool] = None,
    fact_check_status: Optional[str] = None,
    note_status: Optional[str] = None
) -> Query:
    """
    Apply status filters (fact check and note) to a query.
    """
    # Handle note_status if provided
    if note_status:
        if note_status == "not_submitted":
            # Notes that exist but were not submitted
            query = query.where(
                and_(
                    exists().where(
                        and_(
                            FactCheck.post_uid == Post.post_uid,
                            Note.fact_check_id == FactCheck.fact_check_id
                        )
                    ),
                    ~exists().where(
                        and_(
                            FactCheck.post_uid == Post.post_uid,
                            Note.fact_check_id == FactCheck.fact_check_id,
                            Submission.note_id == Note.note_id
                        )
                    )
                )
            )
        elif note_status == "submitted":
            # Notes that were submitted (any status)
            query = query.where(
                exists().where(
                    and_(
                        FactCheck.post_uid == Post.post_uid,
                        Note.fact_check_id == FactCheck.fact_check_id,
                        Submission.note_id == Note.note_id
                    )
                )
            )
        elif note_status == "rated_helpful":
            # Notes rated helpful (status: displayed)
            query = query.where(
                exists().where(
                    and_(
                        FactCheck.post_uid == Post.post_uid,
                        Note.fact_check_id == FactCheck.fact_check_id,
                        Submission.note_id == Note.note_id,
                        Submission.status == "displayed"
                    )
                )
            )
        elif note_status == "rated_unhelpful":
            # Notes rated unhelpful (status: not_displayed)
            query = query.where(
                exists().where(
                    and_(
                        FactCheck.post_uid == Post.post_uid,
                        Note.fact_check_id == FactCheck.fact_check_id,
                        Submission.note_id == Note.note_id,
                        Submission.status == "not_displayed"
                    )
                )
            )
        elif note_status == "needs_more_ratings":
            # Notes that need more ratings (status: submitted)
            query = query.where(
                exists().where(
                    and_(
                        FactCheck.post_uid == Post.post_uid,
                        Note.fact_check_id == FactCheck.fact_check_id,
                        Submission.note_id == Note.note_id,
                        Submission.status == "submitted"
                    )
                )
            )

    # Handle fact_check_status if provided (overrides has_fact_check and has_note)
    if fact_check_status:
        fact_check_exists = exists().where(
            and_(
                FactCheck.post_uid == Post.post_uid,
                FactCheck.status == "completed"
            )
        )

        note_written_exists = exists().where(
            and_(
                FactCheck.post_uid == Post.post_uid,
                Note.fact_check_id == FactCheck.fact_check_id,
                ~exists().where(Submission.note_id == Note.note_id)  # Note exists but not submitted
            )
        )

        note_submitted_exists = exists().where(
            and_(
                FactCheck.post_uid == Post.post_uid,
                Note.fact_check_id == FactCheck.fact_check_id,
                Submission.note_id == Note.note_id
            )
        )

        if fact_check_status == "no_fact_check":
            query = query.where(~fact_check_exists)
        elif fact_check_status == "fact_checked":
            # Has fact check but no notes at all
            note_exists = exists().where(
                and_(
                    FactCheck.post_uid == Post.post_uid,
                    Note.fact_check_id == FactCheck.fact_check_id
                )
            )
            query = query.where(and_(fact_check_exists, ~note_exists))
        elif fact_check_status == "note_written":
            query = query.where(note_written_exists)
        elif fact_check_status == "note_submitted":
            query = query.where(note_submitted_exists)
    else:
        # Use the legacy boolean filters if fact_check_status not provided
        # Add has_fact_check filter
        if has_fact_check is not None:
            fact_check_exists = exists().where(
                and_(
                    FactCheck.post_uid == Post.post_uid,
                    FactCheck.status == "completed"  # Only count completed fact checks
                )
            )
            if has_fact_check:
                query = query.where(fact_check_exists)
            else:
                query = query.where(~fact_check_exists)

        # Add has_note filter
        if has_note is not None:
            note_exists = exists().where(
                and_(
                    FactCheck.post_uid == Post.post_uid,
                    Note.fact_check_id == FactCheck.fact_check_id,
                    Submission.note_id == Note.note_id
                )
            )
            if has_note:
                query = query.where(note_exists)
            else:
                query = query.where(~note_exists)

    return query


def apply_date_filters(
    query: Query,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None
) -> Query:
    """
    Apply date range filters to a query.
    """
    if created_after:
        query = query.where(Post.created_at >= created_after)

    if created_before:
        query = query.where(Post.created_at <= created_before)

    return query


async def batch_fetch_post_metadata(
    session: AsyncSession,
    post_uids: List[str]
) -> Tuple[Dict[str, Any], Dict[str, bool], Dict[str, List[ClassificationPublicResponse]]]:
    """
    Batch fetch metadata for multiple posts in a single query.
    Returns dictionaries mapping post_uid to submissions, fact_check status, and classifications.
    """
    submissions_by_post = {}
    has_fact_check_by_post = {}
    classifications_by_post = {}
    
    if not post_uids:
        return submissions_by_post, has_fact_check_by_post, classifications_by_post
    
    # Batch fetch submissions
    submission_query = (
        select(FactCheck.post_uid, Submission)
        .join(Note, Note.fact_check_id == FactCheck.fact_check_id)
        .join(Submission, Submission.note_id == Note.note_id)
        .where(FactCheck.post_uid.in_(post_uids))
        .order_by(FactCheck.post_uid, Submission.submitted_at.desc())
    )
    submission_result = await session.execute(submission_query)
    
    for post_uid, submission in submission_result:
        if post_uid not in submissions_by_post:
            submissions_by_post[post_uid] = submission
    
    # Batch fetch fact check status (only completed fact checks)
    fact_check_query = (
        select(FactCheck.post_uid, func.count(FactCheck.fact_check_id))
        .where(
            and_(
                FactCheck.post_uid.in_(post_uids),
                FactCheck.status == "completed"  # Only count completed fact checks
            )
        )
        .group_by(FactCheck.post_uid)
    )
    fact_check_result = await session.execute(fact_check_query)
    
    for post_uid, count in fact_check_result:
        has_fact_check_by_post[post_uid] = count > 0
    
    # Set default false for posts without fact checks
    for post_uid in post_uids:
        if post_uid not in has_fact_check_by_post:
            has_fact_check_by_post[post_uid] = False
    
    # Batch fetch classifications
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
    
    return submissions_by_post, has_fact_check_by_post, classifications_by_post


def build_post_response(
    post: Post,
    submission: Optional[Any] = None,
    has_fact_check: bool = False,
    classifications: List[ClassificationPublicResponse] = None,
    include_raw_json: bool = False
) -> PostWithClassificationsResponse:
    """
    Build a PostWithClassificationsResponse from a post and its metadata.
    """
    return PostWithClassificationsResponse(
        post_uid=post.post_uid,
        platform=post.platform,
        platform_post_id=post.platform_post_id,
        author_handle=post.author_handle,
        text=post.text,
        created_at=post.created_at,
        ingested_at=post.ingested_at,
        has_note=submission is not None,
        has_fact_check=has_fact_check,
        submission_status=submission.status if submission else None,
        topic_slug=None,
        topic_display_name=None,
        generated_at=None,
        raw_json=post.raw_json if include_raw_json else None,
        classifications=classifications or []
    )


async def get_posts_with_filters(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    filters_dict: Dict[str, Any] = None,
    has_fact_check: Optional[bool] = None,
    has_note: Optional[bool] = None,
    fact_check_status: Optional[str] = None,
    note_status: Optional[str] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    include_raw_json: bool = False
) -> Tuple[List[PostWithClassificationsResponse], int]:
    """
    Get posts with all filters applied and return both posts and total count.
    """
    # Build base query
    query = select(Post)

    # Apply classification filters
    if filters_dict:
        query = await apply_classification_filters(query, filters_dict)

    # Apply search filter
    if search:
        search_term = f"%{search.strip()}%"
        query = query.where(Post.text.ilike(search_term))

    # Apply status filters
    query = apply_status_filters(query, has_fact_check, has_note, fact_check_status, note_status)

    # Apply date filters
    query = apply_date_filters(query, created_after, created_before)

    # Get total count before pagination
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # Apply ordering and pagination
    # Sort by ingestion date (when we ingested it) instead of tweet creation date
    #query = query.order_by(Post.ingested_at.desc())
    # Old: Sort by tweet creation date
    query = query.order_by(Post.created_at.desc().nulls_last(), Post.ingested_at.desc())
    query = query.limit(limit).offset(offset)
    
    # Execute query
    result = await session.execute(query)
    posts_data = result.scalars().all()
    
    # Get all post UIDs for batch fetching
    post_uids = [post.post_uid for post in posts_data]
    
    # Batch fetch all metadata
    submissions_by_post, has_fact_check_by_post, classifications_by_post = await batch_fetch_post_metadata(
        session, post_uids
    )
    
    # Build response objects
    posts = []
    for post in posts_data:
        posts.append(build_post_response(
            post=post,
            submission=submissions_by_post.get(post.post_uid),
            has_fact_check=has_fact_check_by_post.get(post.post_uid, False),
            classifications=classifications_by_post.get(post.post_uid, []),
            include_raw_json=include_raw_json
        ))
    
    return posts, total


async def get_single_post_with_metadata(
    session: AsyncSession,
    post_uid: str
) -> Optional[PostWithClassificationsResponse]:
    """
    Get a single post with all its metadata.
    """
    # Query for the post
    query = select(Post).where(Post.post_uid == post_uid)
    result = await session.execute(query)
    post = result.scalar_one_or_none()
    
    if not post:
        return None
    
    # Batch fetch metadata for this single post
    submissions_by_post, has_fact_check_by_post, classifications_by_post = await batch_fetch_post_metadata(
        session, [post_uid]
    )
    
    return build_post_response(
        post=post,
        submission=submissions_by_post.get(post_uid),
        has_fact_check=has_fact_check_by_post.get(post_uid, False),
        classifications=classifications_by_post.get(post_uid, []),
        include_raw_json=True  # Include raw JSON for detail view
    )