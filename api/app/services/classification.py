"""Classification service for running classifiers on posts"""

from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_, update
from sqlalchemy.sql import func
import structlog
import asyncio

from app.models import Post, Classifier, Classification
from app.classifiers import ClassifierRegistry
from app.database import async_session_factory
from sqlalchemy import delete, and_

logger = structlog.get_logger()


async def delete_classifications_for_posts(
    post_uids: List[str],
    classifier_slugs: Optional[List[str]] = None
) -> int:
    """
    Delete classifications for specified posts and optionally specific classifiers
    
    Args:
        post_uids: List of post UIDs to delete classifications for
        classifier_slugs: Optional list of specific classifier slugs to delete.
                         If None or empty, no deletions are performed.
    
    Returns:
        Number of classifications deleted
    """
    if not post_uids:
        logger.warning("No post UIDs provided for deletion")
        return 0
    
    if not classifier_slugs:
        logger.warning("No classifier slugs specified, skipping deletion")
        return 0
    
    # Delete specific classifications for all posts in one query
    logger.info(f"Deleting classifications for {len(post_uids)} posts, classifiers: {classifier_slugs}")
    
    async with async_session_factory() as session:
        result = await session.execute(
            delete(Classification).where(
                and_(
                    Classification.post_uid.in_(post_uids),
                    Classification.classifier_slug.in_(classifier_slugs)
                )
            )
        )
        
        await session.commit()
        deleted_count = result.rowcount
    
    logger.info(f"Deleted {deleted_count} classifications")
    
    return deleted_count


async def classify_post(
    post_uid: str, 
    classifier_slugs: Optional[List[str]] = None,
    trigger_fact_checks: bool = True
) -> Dict[str, Any]:
    """
    Run classifiers on a single post
    
    Args:
        post_uid: The post to classify
        classifier_slugs: Optional list of specific classifiers to run.
                         If None, runs all active classifiers.
        trigger_fact_checks: Whether to trigger eligible fact checks after classification
    
    Returns:
        Dictionary with classification results and fact check triggering info
    """
    logger.info("Starting classification", post_uid=post_uid)
    
    # Get the post and classifiers from the database
    async with async_session_factory() as session:
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
            logger.info(f"Running specific classifiers: {classifier_slugs}")
            classifier_query = select(Classifier).where(
                and_(
                    Classifier.slug.in_(classifier_slugs),
                    Classifier.is_active == True
                )
            )
        else:
            # Run all active classifiers
            logger.info("Running all active classifiers")
            classifier_query = select(Classifier).where(Classifier.is_active == True)
        
        classifier_result = await session.execute(classifier_query)
        classifiers = classifier_result.scalars().all()
        
        if not classifiers:
            logger.warning("No active classifiers found")
            return {"classified": 0, "skipped": 0, "errors": []}
        
        # Prepare post data for classifiers (same structure as fact checkers)
        post_data = {
            "post_uid": post.post_uid,
            "text": post.text,
            "author_handle": post.author_handle,
            "platform": post.platform,
            "raw_json": post.raw_json,
            # Include existing classifications if needed
            "classifications": []
        }
    
    # Run classifiers in parallel
    async def classify_with_model(classifier_model):
        """Run a single classifier on the post"""
        try:
            # Check if classification already exists with a fresh session
            async with async_session_factory() as session:
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
                    return {"skipped": 1}
            
            # Get classifier instance with schema - this happens OUTSIDE any session
            classifier = ClassifierRegistry.get_instance(
                classifier_model.slug,
                output_schema=classifier_model.output_schema,
                config=classifier_model.config
            )
            
            if not classifier:
                logger.warning("Classifier not found in registry", slug=classifier_model.slug)
                return {"error": f"Classifier {classifier_model.slug} not found in registry"}
            
            # Run classification - this is the long-running operation
            logger.info(f"Running classifier {classifier_model.slug} for {post_uid}")
            classification_data = await classifier.classify(post_data)
            
            # Store result with a fresh session
            async with async_session_factory() as session:
                classification = Classification(
                    post_uid=post_uid,
                    classifier_slug=classifier_model.slug,
                    classification_data=classification_data
                )
                session.add(classification)
                await session.commit()
                
                logger.info(
                    "Classification complete",
                    post_uid=post_uid,
                    classifier=classifier_model.slug,
                    result=classification_data
                )
                
                return {"classified": 1}
            
        except Exception as e:
            logger.error(
                "Classification failed",
                post_uid=post_uid,
                classifier=classifier_model.slug,
                error=str(e)
            )
            return {"error": {"classifier": classifier_model.slug, "error": str(e)}}
    
    # Run all classifiers in parallel
    tasks = [classify_with_model(cm) for cm in classifiers]
    classifier_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Aggregate results
    results = {
        "classified": 0,
        "skipped": 0,
        "errors": []
    }
    
    for result in classifier_results:
        if isinstance(result, Exception):
            results["errors"].append({"error": str(result)})
        elif isinstance(result, dict):
            if "classified" in result:
                results["classified"] += result["classified"]
            elif "skipped" in result:
                results["skipped"] += result["skipped"]
            elif "error" in result:
                results["errors"].append(result["error"])
    
    # Update post classified_at timestamp if we classified anything
    if results["classified"] > 0:
        async with async_session_factory() as session:
            await session.execute(
                update(Post)
                .where(Post.post_uid == post_uid)
                .values(classified_at=func.now())
            )
            await session.commit()
    
    # Trigger fact checks if requested and classifications were successful
    fact_check_results = {}
    if trigger_fact_checks and (results["classified"] > 0 or results["skipped"] > 0):
        logger.info(f"Triggering fact check evaluation for {post_uid}")
        try:
            from app.services.fact_check_automation import trigger_eligible_fact_checks
            # fact_check_automation now manages its own sessions
            fact_check_results = await trigger_eligible_fact_checks(post_uid)
            logger.info(
                f"Fact check triggering complete",
                post_uid=post_uid,
                triggered=fact_check_results.get("triggered", []),
                skipped=fact_check_results.get("skipped", [])
            )
        except Exception as e:
            logger.error(f"Failed to trigger fact checks for {post_uid}: {e}")
            fact_check_results = {"error": str(e)}
    
    # Add fact check results to return value
    results["fact_checks"] = fact_check_results
    
    return results


async def classify_posts_batch(
    post_uids: List[str],
    classifier_slugs: Optional[List[str]] = None,
    max_concurrent: int = 10,
    trigger_fact_checks: bool = True
) -> Dict[str, Any]:
    """
    Classify multiple posts in parallel
    
    Args:
        post_uids: List of post UIDs to classify
        classifier_slugs: Optional list of specific classifiers to run
        max_concurrent: Maximum concurrent classifications
        trigger_fact_checks: Whether to trigger fact checks after classification
    
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
    
    # Run classifications in parallel with semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def classify_with_semaphore(post_uid):
        async with semaphore:
            # Call classify_post without session parameter
            return await classify_post(post_uid, classifier_slugs, trigger_fact_checks)
    
    tasks = [classify_with_semaphore(uid) for uid in post_uids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            error_msg = f"Error classifying {post_uids[i]}: {str(result)}"
            logger.error(error_msg)
            total_results["total_errors"].append(error_msg)
        else:
            total_results["posts_processed"] += 1
            total_results["total_classified"] += result.get("classified", 0)
            total_results["total_skipped"] += result.get("skipped", 0)
            if result.get("errors"):
                total_results["total_errors"].extend(result.get("errors", []))
    
    logger.info(
        "Batch classification complete",
        processed=total_results["posts_processed"],
        classified=total_results["total_classified"],
        skipped=total_results["total_skipped"],
        errors=len(total_results["total_errors"])
    )
    
    # Return with keys that match what classification_jobs expects
    return {
        "total_classified": total_results["total_classified"],
        "total_skipped": total_results["total_skipped"],
        "errors": total_results["total_errors"]
    }
