"""
Fact Check Automation Service

Handles automatic triggering of fact checkers based on classification results.
Called after all classifications complete for a post.
"""

import asyncio
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import structlog

from app.models import Post, FactChecker
from app.fact_checkers import FactCheckerRegistry
from app.database import async_session_factory

logger = structlog.get_logger()

# Global semaphore to limit concurrent fact checks across ALL callers
# This should be the ONLY semaphore for fact checks in the entire system
GLOBAL_FACT_CHECK_SEMAPHORE = asyncio.Semaphore(15)


async def get_active_fact_checkers() -> List[Dict[str, Any]]:
    """
    Get only active fact checkers from the database.
    Returns fact checkers that are marked as active in the database.

    Returns:
        List of fact checker information dicts with slug, name, description, version
    """
    # Get active fact checkers from database
    async with async_session_factory() as session:
        result = await session.execute(
            select(FactChecker).where(FactChecker.is_active == True)
        )
        active_checkers = result.scalars().all()

    # Return as list of dicts matching the format expected by existing code
    return [
        {
            "slug": checker.slug,
            "name": checker.name,
            "description": checker.description,
            "version": checker.version
        }
        for checker in active_checkers
    ]


async def trigger_eligible_fact_checks(
    post_uid: str,
    fact_checker_slugs: Optional[List[str]] = None,
    execute_immediately: bool = True
) -> Dict[str, Any]:
    """
    Evaluate fact checkers and trigger eligible ones.
    Called after all classifications complete.
    
    Args:
        post_uid: The post to evaluate for fact checking
        fact_checker_slugs: Optional list of specific fact checkers to evaluate. 
                          If None, evaluates all active fact checkers.
        execute_immediately: If True, executes fact checks immediately (old behavior).
                           If False, returns the fact checks to run without executing.
    
    Returns:
        Dictionary with results of triggering fact checks
    """
    logger.info(f"Evaluating fact check eligibility for {post_uid}")
    
    # Get post with all classifications
    async with async_session_factory() as session:
        result = await session.execute(
            select(Post)
            .options(selectinload(Post.classifications))
            .where(Post.post_uid == post_uid)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            logger.error(f"Post {post_uid} not found")
            return {"error": "Post not found", "post_uid": post_uid}
        
        # Prepare data for eligibility checks
        post_data = {
            "post_uid": post.post_uid,
            "text": post.text,
            "author_handle": post.author_handle,
            "platform": post.platform,
            "raw_json": post.raw_json
        }
        
        # Convert classifications to the format expected by fact checkers
        classifications = [
            {
                "classifier_slug": c.classifier_slug,
                "classification_data": c.classification_data,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in (post.classifications or [])
        ]
    
    # Import here to avoid circular dependency
    from app.services.fact_checking import run_fact_check
    
    # Parallel evaluation of fact checkers
    async def evaluate_and_run_checker(checker_info):
        """Evaluate if a fact checker should run and immediately trigger it if yes"""
        checker_slug = checker_info["slug"]
        
        try:
            # Get checker instance
            checker = FactCheckerRegistry.get_instance(checker_slug)
            if not checker:
                logger.warning(f"Could not instantiate fact checker {checker_slug}")
                return {"checker": checker_slug, "status": "error", "error": "Could not instantiate"}
            
            # Check if it should run
            result = await checker.should_run(post_data, classifications)
            should_run = result.get("should_run", False)
            reason = result.get("reason", "No reason provided")
            
            if should_run:
                logger.info(f"Triggering {checker_slug} for {post_uid}: {reason}")
                
                if execute_immediately:
                    # Execute immediately - semaphore is handled inside run_fact_check
                    try:
                        await run_fact_check(
                            post_uid=post_uid,
                            fact_checker_slug=checker_slug,
                            force=False
                        )
                        return {"checker": checker_slug, "status": "triggered", "reason": reason}
                    except Exception as e:
                        logger.error(
                            f"Failed to run fact check {checker_slug} on {post_uid}: {e}"
                        )
                        return {"checker": checker_slug, "status": "error", "error": str(e)}
                else:
                    # New behavior: return the fact check to run
                    return {
                        "checker": checker_slug, 
                        "status": "to_trigger", 
                        "reason": reason,
                        "post_uid": post_uid,
                        "run_function": run_fact_check
                    }
            else:
                logger.debug(f"Skipping {checker_slug} for {post_uid}: {reason}")
                return {"checker": checker_slug, "status": "skipped", "reason": reason}
                
        except Exception as e:
            logger.error(f"Error evaluating {checker_slug} for {post_uid}: {e}")
            return {"checker": checker_slug, "status": "error", "error": str(e)}
    
    # Get fact checkers to evaluate
    if fact_checker_slugs:
        # When specific slugs are provided, get those from the registry
        # This allows manual triggering of specific fact checkers regardless of active status
        all_checkers = FactCheckerRegistry.list_all()
        checkers_to_evaluate = [
            checker for checker in all_checkers
            if checker["slug"] in fact_checker_slugs
        ]
    else:
        # For automatic triggering, only use active fact checkers from database
        checkers_to_evaluate = await get_active_fact_checkers()
    
    # Run all evaluations in parallel
    evaluation_tasks = [evaluate_and_run_checker(checker_info) for checker_info in checkers_to_evaluate]
    evaluation_results = await asyncio.gather(*evaluation_tasks, return_exceptions=True)
    
    # Process results
    triggered = []
    to_trigger = []  # New: collect fact checks to run
    skipped = []
    errors = []
    
    for result in evaluation_results:
        if isinstance(result, Exception):
            errors.append({"error": str(result)})
        elif isinstance(result, dict):
            checker = result.get("checker", "unknown")
            status = result.get("status")
            
            if status == "triggered":
                triggered.append(checker)
            elif status == "to_trigger":
                # New status: fact check should run but wasn't executed yet
                to_trigger.append(result)
            elif status == "skipped":
                skipped.append(checker)
            elif status == "error":
                errors.append({"checker": checker, "error": result.get("error", "Unknown error")})
    
    result_summary = {
        "post_uid": post_uid,
        "triggered": triggered,
        "to_trigger": to_trigger,  # Include fact checks to run
        "skipped": skipped,
        "errors": errors,
        "total_evaluated": len(triggered) + len(to_trigger) + len(skipped) + len(errors)
    }
    
    logger.info(
        f"Fact check evaluation complete for {post_uid}",
        triggered_count=len(triggered),
        skipped_count=len(skipped),
        error_count=len(errors)
    )
    
    return result_summary


async def run_fact_checks_batch(
    post_uids: List[str]
) -> Dict[str, Any]:
    """
    Trigger fact checks for multiple posts.
    
    Args:
        post_uids: List of post UIDs to evaluate
    
    Returns:
        Aggregated results
    """
    logger.info(f"Starting batch fact check evaluation for {len(post_uids)} posts")
    
    total_triggered = []
    total_skipped = []
    total_errors = []
    posts_processed = 0
    
    for post_uid in post_uids:
        try:
            result = await trigger_eligible_fact_checks(post_uid)
            
            if "error" not in result:
                posts_processed += 1
                total_triggered.extend(result.get("triggered", []))
                total_skipped.extend(result.get("skipped", []))
                total_errors.extend(result.get("errors", []))
            else:
                total_errors.append({
                    "post_uid": post_uid,
                    "error": result.get("error")
                })
        except Exception as e:
            logger.error(f"Failed to evaluate fact checks for {post_uid}: {e}")
            total_errors.append({
                "post_uid": post_uid,
                "error": str(e)
            })
    
    # Count unique fact checkers triggered
    unique_triggered = len(set(total_triggered))
    
    return {
        "posts_processed": posts_processed,
        "total_triggered": len(total_triggered),
        "unique_fact_checkers_triggered": unique_triggered,
        "total_skipped": len(total_skipped),
        "total_errors": len(total_errors),
        "errors": total_errors[:10]  # Limit error details to first 10
    }