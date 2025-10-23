"""
Fact Checking Service

Handles running fact checkers on posts and managing results.
"""

import asyncio
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import structlog
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import async_session_factory
from app.fact_checkers import FactCheckerRegistry
from app.fact_checkers.shared.enums import DEFAULT_VERDICT, NOTE_WRITING_VERDICTS
from app.models import FactCheck, FactChecker, Post
from app.services import note_writing

logger = structlog.get_logger()


def clean_utm_params(data: Union[dict, list, str, Any]) -> Union[dict, list, str, Any]:
    """
    Recursively clean UTM parameters from URLs in any data structure.

    Args:
        data: Any data structure that might contain URLs with UTM params

    Returns:
        The same data structure with UTM params removed from all URLs
    """
    if isinstance(data, str):
        # Remove ?utm_source=openai from strings
        return re.sub(r'\?utm_source=openai(?:&[^&\s]*)*', '', data)
    elif isinstance(data, dict):
        return {key: clean_utm_params(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [clean_utm_params(item) for item in data]
    else:
        # For other types (numbers, booleans, None, etc.), return as-is
        return data


async def _update_fact_check_status(
    session: AsyncSession,
    fact_check_id: str,
    status: str,
    **kwargs
) -> None:
    """Helper to update fact check status in database"""
    check_uuid = uuid.UUID(fact_check_id)
    values = {"status": status}
    values.update(kwargs)

    await session.execute(
        update(FactCheck)
        .where(FactCheck.fact_check_id == check_uuid)
        .values(**values)
    )
    await session.commit()


def _build_fact_check_response(fact_check, fact_checker=None) -> dict[str, Any]:
    """Build a standardized fact check response"""
    response = {
        "id": str(fact_check.fact_check_id),
        "status": fact_check.status,
        "body": fact_check.body,
        "raw_json": clean_utm_params(fact_check.raw_json) if fact_check.raw_json else None,
        "verdict": fact_check.verdict,
        "confidence": float(fact_check.confidence) if fact_check.confidence else None,
        "claims": fact_check.claims,
        "created_at": fact_check.created_at.isoformat()
    }

    if hasattr(fact_check, 'error_message'):
        response["error_message"] = fact_check.error_message

    if hasattr(fact_check, 'updated_at'):
        response["updated_at"] = fact_check.updated_at.isoformat()

    if hasattr(fact_check, 'post_uid'):
        response["post_uid"] = fact_check.post_uid

    if fact_checker:
        response["fact_checker"] = {
            "slug": fact_checker.slug,
            "name": fact_checker.name,
        }
        if hasattr(fact_checker, 'version'):
            response["fact_checker"]["version"] = fact_checker.version

    return response


async def _run_fact_check_background(
    fact_check_id: str,
    fact_checker_slug: str,
    post_data: dict[str, Any]
) -> None:
    """
    Background task to run a fact checker and update the database with progress

    Args:
        fact_check_id: ID of the fact check record to update
        fact_checker_slug: The fact checker to run
        post_data: Post data to check
    """
    # Import and acquire the global semaphore FIRST
    from app.services.fact_check_automation import GLOBAL_FACT_CHECK_SEMAPHORE
    
    async with GLOBAL_FACT_CHECK_SEMAPHORE:
        logger.info(f"Acquired semaphore for fact check {fact_check_id}")
        try:
            # Update status to processing with a fresh session
            async with async_session_factory() as session:
                await _update_fact_check_status(
                    session, fact_check_id, "processing",
                    check_metadata={"started_at": datetime.utcnow().isoformat()}
                )

            # Get the fact checker instance OUTSIDE the session context
            fact_checker = FactCheckerRegistry.get_instance(fact_checker_slug)
            if not fact_checker:
                # Update error status with a fresh session
                async with async_session_factory() as session:
                    await _update_fact_check_status(
                        session, fact_check_id, "failed",
                        error_message=f"Fact checker {fact_checker_slug} not found",
                        check_metadata={"failed_at": datetime.utcnow().isoformat()}
                    )
                return

            logger.info(f"Running fact checker {fact_checker_slug}",
                       fact_check_id=fact_check_id)

            # Stream updates - this is the long-running operation that doesn't need a persistent session
            updates = []
            final_update = {}
            
            async for update in fact_checker.stream_fact_check(post_data):
                final_update = update

                # Accumulate updates if provided
                if "updates" in update and update["updates"]:
                    updates = update["updates"]
            
                # Prepare values for database update
                update_values = {
                    "raw_json": clean_utm_params({
                        "fact_check_id": fact_check_id,
                        "updates": updates,
                    })
                }

                # Add optional fields
                if update.get("verdict"):
                    update_values["verdict"] = update["verdict"]
                if update.get("body"):
                    update_values["body"] = update["body"]
                if update.get("confidence") is not None:
                    update_values["confidence"] = update["confidence"]
            
                # Create a fresh session for each update - this is intentional!
                # The streaming could take minutes, so we don't want to hold a session open
                async with async_session_factory() as session:
                    await _update_fact_check_status(session, fact_check_id, "processing", **update_values)
            
                logger.debug(f"Updated fact check with {len(updates)} updates",
                           fact_check_id=fact_check_id)

            # Prepare final metadata
            check_metadata = {
                "completed_at": datetime.utcnow().isoformat(),
                "fact_checker": fact_checker_slug,
            }

            # Add optional metadata from final update
            for key in ["is_eligible", "eligibility_reason"]:
                if final_update.get(key) is not None:
                    check_metadata[key] = final_update[key]

            if final_update.get("metadata"):
                check_metadata.update(final_update["metadata"])

            # Check if the fact check is ineligible
            is_ineligible = final_update.get("is_eligible") == False
            
            # Set appropriate status
            final_status = "ineligible" if is_ineligible else "completed"

            # Mark with final results using a fresh session
            async with async_session_factory() as session:
                await _update_fact_check_status(
                    session, fact_check_id, final_status,
                    body=final_update.get("body", "Not eligible for fact checking" if is_ineligible else "No body generated"),
                    raw_json=clean_utm_params({
                        "fact_check_id": fact_check_id,
                        "updates": updates,
                    }),
                    verdict=final_update.get("verdict", DEFAULT_VERDICT),
                    confidence=final_update.get("confidence", 0.0),
                    check_metadata=check_metadata,
                    claims=final_update.get("claims")
                )

            logger.info(f"Fact check {final_status}",
                       fact_check_id=fact_check_id,
                       verdict=final_update.get("verdict"),
                       is_eligible=final_update.get("is_eligible"))

            # Only auto-trigger note writers for eligible completed fact checks
            # Note: Community notes cannot be accepted if the conclusion is positive (true)
            if final_status == "completed" and final_update.get("verdict") in NOTE_WRITING_VERDICTS:
                try:
                    # Note writing should manage its own session
                    await note_writing.auto_write_notes_for_fact_check(
                        fact_check_id=fact_check_id,
                        platform=post_data["platform"]
                    )
                    logger.info(f"Auto-triggered note writers for fact check {fact_check_id}")
                except Exception as note_error:
                    logger.error(f"Failed to auto-trigger note writers: {note_error}",
                               fact_check_id=fact_check_id)
            elif final_status == "completed" and final_update.get("verdict") not in NOTE_WRITING_VERDICTS:
                logger.info(f"Skipping note creation for fact check {fact_check_id} - verdict is {final_update.get('verdict')}",
                           fact_check_id=fact_check_id)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in fact checker: {error_msg}",
                        fact_check_id=fact_check_id,
                        fact_checker=fact_checker_slug)

            # Try to update error status with a fresh session
            try:
                async with async_session_factory() as session:
                    await _update_fact_check_status(
                        session, fact_check_id, "failed",
                        error_message=error_msg,
                        check_metadata={
                            "failed_at": datetime.utcnow().isoformat(),
                            "error": error_msg
                        }
                    )
            except Exception as update_error:
                logger.error(f"Failed to update error status: {update_error}",
                           fact_check_id=fact_check_id)


async def run_fact_check(
    post_uid: str,
    fact_checker_slug: str,
    force: bool = False
) -> dict[str, Any]:
    """
    Run a specific fact checker on a post

    Args:
        post_uid: The post to check
        fact_checker_slug: The fact checker to use
        force: If True, rerun even if a result exists

    Returns:
        Dict with fact check result
    """
    # Create our own session for this operation
    async with async_session_factory() as session:
        # Get the post
        result = await session.execute(
            select(Post)
            .options(selectinload(Post.classifications))
            .where(Post.post_uid == post_uid)
        )
        post = result.scalar_one_or_none()

        if not post:
            raise ValueError(f"Post {post_uid} not found")

        # Get or create fact checker record
        result = await session.execute(
            select(FactChecker).where(FactChecker.slug == fact_checker_slug)
        )
        fact_checker_record = result.scalar_one_or_none()

        if not fact_checker_record:
            # Create fact checker record if it doesn't exist
            fact_checker_instance = FactCheckerRegistry.get_instance(fact_checker_slug)
            if not fact_checker_instance:
                raise ValueError(f"Fact checker {fact_checker_slug} not registered")

            fact_checker_record = FactChecker(
                slug=fact_checker_slug,
                name=fact_checker_instance.name,
                description=fact_checker_instance.description,
                version=fact_checker_instance.version,
                is_active=True,
                configuration=fact_checker_instance.get_configuration()
            )
            session.add(fact_checker_record)
            await session.flush()

        # Check if we already have a result
        if not force:
            result = await session.execute(
                select(FactCheck).where(
                    and_(
                        FactCheck.post_uid == post_uid,
                        FactCheck.fact_checker_id == fact_checker_record.fact_checker_id,
                        FactCheck.status == "completed"
                    )
                )
            )
            existing_check = result.scalar_one_or_none()

            if existing_check:
                logger.info(f"Returning existing fact check for {post_uid} with {fact_checker_slug}")
                return _build_fact_check_response(existing_check)

        # Delete any existing check if forcing
        if force:
            delete_result = await session.execute(
                select(FactCheck).where(
                    and_(
                        FactCheck.post_uid == post_uid,
                        FactCheck.fact_checker_id == fact_checker_record.fact_checker_id
                    )
                )
            )
            existing = delete_result.scalar_one_or_none()
            if existing:
                await session.delete(existing)
                await session.flush()

        # Create a new fact check record with pending status
        fact_check = FactCheck(
            post_uid=post_uid,
            fact_checker_id=fact_checker_record.fact_checker_id,
            status="pending",
            raw_json=clean_utm_params({"updates": []}),  # Initialize with empty updates array, cleaned
            check_metadata={"started_at": datetime.utcnow().isoformat()}
        )
        session.add(fact_check)
        await session.commit()  # Commit immediately so the record exists

        fact_check_id = str(fact_check.fact_check_id)

        # Prepare post data for the background task
        post_data = {
            "post_uid": post.post_uid,
            "text": post.text,
            "author_handle": post.author_handle,
            "platform": post.platform,
            "raw_json": post.raw_json,
            "classifications": [
                {
                    "classifier_slug": c.classifier_slug,
                    "classification_data": c.classification_data
                }
                for c in (post.classifications or [])
            ]
        }
        
        # Build response before launching background task
        response = _build_fact_check_response(fact_check)

    # Launch background task AFTER closing the session
    # The semaphore control is handled in _run_fact_check_background
    asyncio.create_task(
        _run_fact_check_background(
            fact_check_id=fact_check_id,
            fact_checker_slug=fact_checker_slug,
            post_data=post_data
        )
    )

    logger.info(f"Fact check job started for {post_uid} with {fact_checker_slug}")

    # Return immediately with pending status
    return response


async def get_fact_checks_for_post(
    post_uid: str
) -> list[dict[str, Any]]:
    """
    Get all fact checks for a post

    Args:
        post_uid: The post to get fact checks for

    Returns:
        List of fact check results
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(FactCheck, FactChecker)
            .join(FactChecker)
            .where(FactCheck.post_uid == post_uid)
            .order_by(FactCheck.created_at.desc())
        )

        return [
            _build_fact_check_response(fact_check, fact_checker)
            for fact_check, fact_checker in result
        ]


async def get_fact_check_status(
    fact_check_id: str
) -> Optional[dict[str, Any]]:
    """
    Get the status of a fact check job

    Args:
        fact_check_id: The fact check ID

    Returns:
        Status information or None if not found
    """
    try:
        check_uuid = uuid.UUID(fact_check_id)
    except ValueError:
        return None

    async with async_session_factory() as session:
        result = await session.execute(
            select(FactCheck, FactChecker)
            .join(FactChecker)
            .where(FactCheck.fact_check_id == check_uuid)
        )

        row = result.first()
        if not row:
            return None

        fact_check, fact_checker = row
        return _build_fact_check_response(fact_check, fact_checker)


async def list_available_fact_checkers() -> list[dict[str, Any]]:
    """
    List all available fact checkers

    Returns:
        List of fact checker information
    """
    # Get from registry
    registry_checkers = {c["slug"]: c for c in FactCheckerRegistry.list_all()}

    # Get from database with its own session
    async with async_session_factory() as session:
        result = await session.execute(
            select(FactChecker).where(FactChecker.is_active == True)
        )
        db_checkers = {c.slug: c for c in result.scalars()}

    # Merge information
    checkers = {}

    # Add all registry checkers
    for slug, checker_info in registry_checkers.items():
        checkers[slug] = {
            **checker_info,
            "available": True,
            "in_database": slug in db_checkers,
        }
        if slug in db_checkers:
            checkers[slug]["id"] = str(db_checkers[slug].fact_checker_id)

    # Add database-only checkers (not in registry)
    for slug, checker in db_checkers.items():
        if slug not in checkers:
            checkers[slug] = {
                "slug": checker.slug,
                "name": checker.name,
                "description": checker.description,
                "version": checker.version,
                "available": False,
                "in_database": True,
                "id": str(checker.fact_checker_id)
            }

    return list(checkers.values())


async def count_fact_check_eligible_posts(
    start_date: datetime,
    end_date: datetime,
    fact_checker_slugs: Optional[List[str]] = None,
    force: bool = False
) -> int:
    """
    Count posts in date range that are eligible for fact checking
    
    Args:
        start_date: Start of date range
        end_date: End of date range  
        fact_checker_slugs: Specific fact checkers to check, or None for all active
        force: If True, count all posts regardless of existing fact checks
    
    Returns:
        Count of eligible posts
    """
    from sqlalchemy import and_, not_, exists, or_
    
    logger.info(f"Counting fact check eligible posts from {start_date} to {end_date}", 
                fact_checker_slugs=fact_checker_slugs, force=force)
    
    async with async_session_factory() as session:
        # Base query for posts in date range
        # Use ingested_at since created_at can be NULL
        query = select(Post).where(
            and_(
                Post.ingested_at >= start_date,
                Post.ingested_at <= end_date
            )
        )
        
        # If not forcing, we need to find posts that don't have fact checks from specified checkers
        if not force:
            if fact_checker_slugs:
                # Get fact checker IDs for the specified slugs
                fc_result = await session.execute(
                    select(FactChecker.fact_checker_id).where(
                        FactChecker.slug.in_(fact_checker_slugs)
                    )
                )
                fact_checker_ids = [row[0] for row in fc_result]
                
                # Find posts that are missing fact checks from at least one specified checker
                # This means they need fact checking
                missing_conditions = []
                for fc_id in fact_checker_ids:
                    # Check if this specific fact check doesn't exist or isn't complete
                    subquery = exists().where(
                        and_(
                            FactCheck.post_uid == Post.post_uid,
                            FactCheck.fact_checker_id == fc_id,
                            FactCheck.status.in_(["completed", "ineligible", "processing"])
                        )
                    )
                    missing_conditions.append(not_(subquery))
                
                # Include posts that are missing at least one fact check
                if missing_conditions:
                    query = query.where(or_(*missing_conditions))
            else:
                # For "all active", get active fact checkers from registry
                active_checkers = FactCheckerRegistry.list_all()
                if active_checkers:
                    # Get their IDs from database
                    active_slugs = [c["slug"] for c in active_checkers]
                    fc_result = await session.execute(
                        select(FactChecker.fact_checker_id).where(
                            and_(
                                FactChecker.slug.in_(active_slugs),
                                FactChecker.is_active == True
                            )
                        )
                    )
                    fact_checker_ids = [row[0] for row in fc_result]
                    
                    # Find posts missing at least one active fact checker
                    missing_conditions = []
                    for fc_id in fact_checker_ids:
                        subquery = exists().where(
                            and_(
                                FactCheck.post_uid == Post.post_uid,
                                FactCheck.fact_checker_id == fc_id,
                                FactCheck.status.in_(["completed", "ineligible", "processing"])
                            )
                        )
                        missing_conditions.append(not_(subquery))
                    
                    if missing_conditions:
                        query = query.where(or_(*missing_conditions))
        
        # First count posts just in date range for debugging
        date_range_count_query = select(func.count(Post.post_uid)).where(
            and_(
                Post.ingested_at >= start_date,
                Post.ingested_at <= end_date
            )
        )
        date_range_result = await session.execute(date_range_count_query)
        date_range_count = date_range_result.scalar() or 0
        logger.info(f"Posts in date range: {date_range_count}")
        
        # Count the posts with all filters
        # Use func.count() directly on the filtered query
        count_result = await session.execute(
            select(func.count()).select_from(query.subquery())
        )
        final_count = count_result.scalar() or 0
        logger.info(f"Posts eligible for fact checking: {final_count}")
        return final_count


async def run_batch_fact_checks(
    start_date: datetime,
    end_date: datetime,
    fact_checker_slugs: Optional[List[str]] = None,
    force: bool = False,
    job_id: str = None
) -> Dict[str, Any]:
    """
    Run fact checks on posts within a date range
    
    Args:
        start_date: Start of date range
        end_date: End of date range
        fact_checker_slugs: Specific fact checkers to run, or None for all active
        force: If True, rerun even if fact check already exists
        job_id: Optional job ID for tracking progress
    
    Returns:
        Summary of batch processing results
    
    Note: Fact check concurrency is controlled by GLOBAL_FACT_CHECK_SEMAPHORE (max 20)
    """
    from sqlalchemy import and_, not_, exists, or_
    from app.services.fact_check_automation import trigger_eligible_fact_checks
    
    logger.info(
        f"Starting batch fact check from {start_date} to {end_date}",
        fact_checker_slugs=fact_checker_slugs,
        force=force,
        job_id=job_id,
        max_concurrent=20  # Using GLOBAL_FACT_CHECK_SEMAPHORE
    )
    
    async with async_session_factory() as session:
        # Build query for posts in date range
        # Use ingested_at since created_at can be NULL
        query = select(Post.post_uid).where(
            and_(
                Post.ingested_at >= start_date,
                Post.ingested_at <= end_date
            )
        )
        
        # If not forcing, filter to posts missing fact checks
        if not force:
            if fact_checker_slugs:
                # Get fact checker IDs
                fc_result = await session.execute(
                    select(FactChecker.fact_checker_id, FactChecker.slug).where(
                        FactChecker.slug.in_(fact_checker_slugs)
                    )
                )
                fact_checker_map = {row[1]: row[0] for row in fc_result}
                
                # Build conditions for posts missing at least one fact check
                missing_conditions = []
                for slug, fc_id in fact_checker_map.items():
                    subquery = exists().where(
                        and_(
                            FactCheck.post_uid == Post.post_uid,
                            FactCheck.fact_checker_id == fc_id,
                            FactCheck.status.in_(["completed", "ineligible", "processing"])
                        )
                    )
                    missing_conditions.append(not_(subquery))
                
                if missing_conditions:
                    query = query.where(or_(*missing_conditions))
            else:
                # For all active checkers, get posts that don't have ALL fact checks
                active_checkers = FactCheckerRegistry.list_all()
                if active_checkers:
                    active_slugs = [c["slug"] for c in active_checkers]
                    fc_result = await session.execute(
                        select(FactChecker.fact_checker_id).where(
                            and_(
                                FactChecker.slug.in_(active_slugs),
                                FactChecker.is_active == True
                            )
                        )
                    )
                    fact_checker_ids = [row[0] for row in fc_result]
                    
                    # Find posts missing at least one active fact checker
                    missing_conditions = []
                    for fc_id in fact_checker_ids:
                        subquery = exists().where(
                            and_(
                                FactCheck.post_uid == Post.post_uid,
                                FactCheck.fact_checker_id == fc_id,
                                FactCheck.status.in_(["completed", "ineligible", "processing"])
                            )
                        )
                        missing_conditions.append(not_(subquery))
                    
                    if missing_conditions:
                        query = query.where(or_(*missing_conditions))
        
        # Execute query to get post UIDs
        result = await session.execute(query.order_by(Post.ingested_at.desc()))
        post_uids = [row[0] for row in result]
    
    total_posts = len(post_uids)
    logger.info(f"Found {total_posts} posts to process", job_id=job_id)
    
    # Step 1: Evaluate all posts to determine which fact checks need to run
    # This is fast and can be done with higher concurrency
    EVALUATION_SEMAPHORE = asyncio.Semaphore(50)  # Can evaluate many posts quickly
    
    async def evaluate_post(post_uid):
        """Evaluate which fact checks should run for a post (doesn't execute them)"""
        async with EVALUATION_SEMAPHORE:
            try:
                # Call with execute_immediately=False to just get evaluation results
                result = await trigger_eligible_fact_checks(
                    post_uid=post_uid,
                    fact_checker_slugs=fact_checker_slugs,
                    execute_immediately=False  # Don't execute, just evaluate
                )
                return result
            except Exception as e:
                logger.error(f"Failed to evaluate {post_uid}: {e}", job_id=job_id)
                return {
                    "post_uid": post_uid,
                    "to_trigger": [],
                    "skipped": [],
                    "error": str(e)
                }
    
    # Evaluate all posts in parallel
    logger.info(f"Evaluating {total_posts} posts for fact check eligibility", job_id=job_id)
    evaluation_tasks = [evaluate_post(post_uid) for post_uid in post_uids]
    evaluation_results = await asyncio.gather(*evaluation_tasks)
    
    # Step 2: Collect all fact checks that need to run
    all_fact_checks_to_run = []
    skipped_count = 0
    evaluation_errors = []
    
    for result in evaluation_results:
        if "error" in result and result["error"]:
            evaluation_errors.append(result)
        else:
            # Collect fact checks to run from this post
            for fc in result.get("to_trigger", []):
                all_fact_checks_to_run.append(fc)
            skipped_count += len(result.get("skipped", []))
    
    logger.info(
        f"Evaluation complete. Found {len(all_fact_checks_to_run)} fact checks to run, "
        f"{skipped_count} skipped",
        job_id=job_id
    )
    
    # Step 3: Run fact checks - the semaphore control is handled inside run_fact_check
    
    async def run_single_fact_check(fact_check_info):
        """Run a single fact check (semaphore handled by run_fact_check)"""
        try:
            checker_slug = fact_check_info["checker"]
            post_uid = fact_check_info["post_uid"]
            run_function = fact_check_info["run_function"]
            
            logger.debug(f"Running fact check {checker_slug} for {post_uid}", job_id=job_id)
            
            # Execute the fact check - semaphore is handled inside
            await run_function(
                post_uid=post_uid,
                fact_checker_slug=checker_slug,
                force=force
            )
            
            return {
                "post_uid": post_uid,
                "checker": checker_slug,
                "status": "completed",
                "error": None
            }
        except Exception as e:
            logger.error(
                f"Failed to run fact check {fact_check_info.get('checker')} "
                f"for {fact_check_info.get('post_uid')}: {e}",
                job_id=job_id
            )
            return {
                "post_uid": fact_check_info.get("post_uid"),
                "checker": fact_check_info.get("checker"),
                "status": "failed",
                "error": str(e)
            }
    
    # Run all fact checks with controlled concurrency
    if all_fact_checks_to_run:
        logger.info(
            f"Starting {len(all_fact_checks_to_run)} fact checks with "
            f"max 20 concurrent (via GLOBAL_FACT_CHECK_SEMAPHORE)",
            job_id=job_id
        )
        fact_check_tasks = [run_single_fact_check(fc) for fc in all_fact_checks_to_run]
        fact_check_results = await asyncio.gather(*fact_check_tasks)
    else:
        fact_check_results = []
    
    # Process results
    processed = total_posts - len(evaluation_errors)
    completed_fact_checks = sum(1 for r in fact_check_results if r["status"] == "completed")
    failed_fact_checks = sum(1 for r in fact_check_results if r["status"] == "failed")
    
    # Collect errors
    errors = []
    for err in evaluation_errors[:5]:  # Limit evaluation errors
        errors.append(f"Evaluation error for {err.get('post_uid')}: {err.get('error')}")
    
    for fc_result in fact_check_results:
        if fc_result["status"] == "failed":
            if len(errors) < 10:  # Limit total errors
                errors.append(
                    f"Fact check {fc_result['checker']} failed for "
                    f"{fc_result['post_uid']}: {fc_result['error']}"
                )
    
    return {
        "total_posts": total_posts,
        "processed": processed,
        "fact_checks_triggered": len(all_fact_checks_to_run),
        "fact_checks_completed": completed_fact_checks,
        "fact_checks_failed": failed_fact_checks,
        "skipped": skipped_count,
        "errors": errors
    }
