"""Classification service for running classifiers on posts"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.sql import func
import structlog
import asyncio

from app.models import Post, Classifier, Classification
from app.classifiers import get_classifier

logger = structlog.get_logger()


async def classify_post(
    post_uid: str, 
    session: AsyncSession,
    classifier_slugs: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Run classifiers on a single post
    
    Args:
        post_uid: The post to classify
        session: Database session
        classifier_slugs: Optional list of specific classifiers to run.
                         If None, runs all active classifiers.
    
    Returns:
        Dictionary with classification results
    """
    logger.info("Starting classification", post_uid=post_uid)
    
    # Get the post
    post_result = await session.execute(
        select(Post).where(Post.post_uid == post_uid)
    )
    post = post_result.scalar_one_or_none()
    
    if not post:
        logger.error("Post not found", post_uid=post_uid)
        return {"error": "Post not found", "classified": 0}
    
    # Get classifiers to run
    if classifier_slugs:
        # Run specific classifiers
        classifier_query = select(Classifier).where(
            and_(
                Classifier.slug.in_(classifier_slugs),
                Classifier.is_active == True
            )
        )
    else:
        # Run all active classifiers
        classifier_query = select(Classifier).where(Classifier.is_active == True)
    
    classifier_result = await session.execute(classifier_query)
    classifiers = classifier_result.scalars().all()
    
    if not classifiers:
        logger.warning("No active classifiers found")
        return {"classified": 0, "skipped": 0, "errors": []}
    
    # Prepare post metadata for classifiers
    post_metadata = {
        "platform": post.platform,
        "author_handle": post.author_handle,
        "created_at": post.created_at,
        "ingested_at": post.ingested_at
    }
    
    # Run classifiers
    results = {
        "classified": 0,
        "skipped": 0,
        "errors": []
    }
    
    for classifier_model in classifiers:
        try:
            # Check if classification already exists
            existing = await session.execute(
                select(Classification).where(
                    and_(
                        Classification.post_uid == post_uid,
                        Classification.classifier_slug == classifier_model.slug
                    )
                )
            )
            
            if existing.scalar_one_or_none():
                logger.info(
                    "Classification already exists, skipping",
                    post_uid=post_uid,
                    classifier=classifier_model.slug
                )
                results["skipped"] += 1
                continue
            
            # Get classifier instance with schema from database
            classifier = get_classifier(
                classifier_model.slug,
                output_schema=classifier_model.output_schema,
                config=classifier_model.config
            )
            
            # Run classification
            classification_data = await classifier.classify(
                post.text,
                post_metadata
            )
            
            # Store result
            classification = Classification(
                post_uid=post_uid,
                classifier_slug=classifier_model.slug,
                classification_data=classification_data
            )
            
            session.add(classification)
            results["classified"] += 1
            
            logger.info(
                "Classification complete",
                post_uid=post_uid,
                classifier=classifier_model.slug,
                result=classification_data
            )
            
        except Exception as e:
            logger.error(
                "Classification failed",
                post_uid=post_uid,
                classifier=classifier_model.slug,
                error=str(e)
            )
            results["errors"].append({
                "classifier": classifier_model.slug,
                "error": str(e)
            })
    
    # Update post classified_at timestamp
    if results["classified"] > 0:
        await session.execute(
            update(Post)
            .where(Post.post_uid == post_uid)
            .values(classified_at=func.now())
        )
    
    await session.commit()
    
    return results


async def classify_posts_batch(
    post_uids: List[str],
    session: AsyncSession,
    classifier_slugs: Optional[List[str]] = None,
    parallel: bool = True,
    max_concurrent: int = 5
) -> Dict[str, Any]:
    """
    Classify multiple posts
    
    Args:
        post_uids: List of post UIDs to classify
        session: Database session
        classifier_slugs: Optional list of specific classifiers to run
        parallel: Whether to run classifications in parallel
        max_concurrent: Maximum concurrent classifications (if parallel)
    
    Returns:
        Dictionary with aggregate results
    """
    logger.info(f"Starting batch classification for {len(post_uids)} posts")
    
    total_results = {
        "posts_processed": 0,
        "total_classified": 0,
        "total_skipped": 0,
        "total_errors": []
    }
    
    if parallel:
        # Run classifications in parallel with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def classify_with_semaphore(post_uid):
            async with semaphore:
                return await classify_post(post_uid, session, classifier_slugs)
        
        tasks = [classify_with_semaphore(uid) for uid in post_uids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                total_results["total_errors"].append(str(result))
            else:
                total_results["posts_processed"] += 1
                total_results["total_classified"] += result.get("classified", 0)
                total_results["total_skipped"] += result.get("skipped", 0)
                total_results["total_errors"].extend(result.get("errors", []))
    else:
        # Run classifications sequentially
        for post_uid in post_uids:
            try:
                result = await classify_post(post_uid, session, classifier_slugs)
                total_results["posts_processed"] += 1
                total_results["total_classified"] += result.get("classified", 0)
                total_results["total_skipped"] += result.get("skipped", 0)
                total_results["total_errors"].extend(result.get("errors", []))
            except Exception as e:
                logger.error(f"Failed to classify post {post_uid}: {e}")
                total_results["total_errors"].append(str(e))
    
    logger.info(
        "Batch classification complete",
        processed=total_results["posts_processed"],
        classified=total_results["total_classified"],
        skipped=total_results["total_skipped"],
        errors=len(total_results["total_errors"])
    )
    
    return total_results


async def reclassify_all_posts(
    session: AsyncSession,
    classifier_slug: str,
    force: bool = False
) -> Dict[str, Any]:
    """
    Reclassify all posts with a specific classifier
    
    Args:
        session: Database session
        classifier_slug: The classifier to run
        force: If True, reclassify even if classification exists
    
    Returns:
        Dictionary with results
    """
    logger.info(f"Starting reclassification with {classifier_slug}")
    
    # Get all posts
    if force:
        # Get all posts
        posts_query = select(Post.post_uid)
    else:
        # Get posts without this classification
        posts_query = (
            select(Post.post_uid)
            .outerjoin(
                Classification,
                and_(
                    Classification.post_uid == Post.post_uid,
                    Classification.classifier_slug == classifier_slug
                )
            )
            .where(Classification.classification_id.is_(None))
        )
    
    posts_result = await session.execute(posts_query)
    post_uids = [row[0] for row in posts_result.fetchall()]
    
    if not post_uids:
        logger.info("No posts to classify")
        return {"posts_processed": 0}
    
    logger.info(f"Found {len(post_uids)} posts to classify")
    
    # If forcing, delete existing classifications first
    if force:
        await session.execute(
            Classification.__table__.delete().where(
                Classification.classifier_slug == classifier_slug
            )
        )
        await session.commit()
    
    # Run classification
    return await classify_posts_batch(
        post_uids,
        session,
        classifier_slugs=[classifier_slug],
        parallel=True
    )