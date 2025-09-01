"""Background job tracking for batch classification tasks"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

logger = structlog.get_logger()

# In-memory job storage (replace with Redis or DB in production)
_jobs: Dict[str, Dict[str, Any]] = {}


def create_job(job_id: str, total_posts: int) -> None:
    """Create a new job entry"""
    _jobs[job_id] = {
        "job_id": job_id,
        "total_posts": total_posts,
        "processed": 0,
        "classified": 0,
        "skipped": 0,
        "errors": [],
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "progress_percentage": 0
    }


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get the current status of a job"""
    return _jobs.get(job_id)


def update_job_progress(
    job_id: str, 
    processed: int, 
    classified: int = 0, 
    skipped: int = 0,
    errors: Optional[List[str]] = None
) -> None:
    """Update job progress - processed is the total so far, classified/skipped are increments"""
    if job_id not in _jobs:
        return
    
    job = _jobs[job_id]
    job["processed"] = processed  # This is the running total
    job["classified"] += classified  # These are increments
    job["skipped"] += skipped  # These are increments
    
    if errors:
        job["errors"].extend(errors)
    
    # Calculate progress percentage
    if job["total_posts"] > 0:
        job["progress_percentage"] = int((processed / job["total_posts"]) * 100)
    
    # Check if completed
    if processed >= job["total_posts"]:
        job["status"] = "completed"
        job["completed_at"] = datetime.utcnow().isoformat()


async def run_batch_classification(
    job_id: str,
    post_uids: List[str],
    classifier_slugs: Optional[List[str]],
    force: bool
) -> None:
    """Run batch classification in the background with its own session"""
    from app.database import async_session_factory
    from app.services import classification
    
    # Create a new session for the background task
    async with async_session_factory() as session:
        try:
            logger.info(f"Starting batch classification job {job_id} for {len(post_uids)} posts, force={force}, classifier_slugs={classifier_slugs}")
            
            # If force is True, delete existing classifications first
            if force:
                deleted_count = await classification.delete_classifications_for_posts(
                    session=session,
                    post_uids=post_uids,
                    classifier_slugs=classifier_slugs
                )
                
                if deleted_count == 0 and classifier_slugs:
                    logger.info("No existing classifications to delete")
                elif not classifier_slugs:
                    logger.error("No classifiers specified. Must select at least one classifier to rerun.")
                    return
            
            batch_size = 10  # Process in batches of 10
            processed = 0
            
            for i in range(0, len(post_uids), batch_size):
                batch = post_uids[i:i + batch_size]
                
                try:
                    # Run classification for this batch
                    result = await classification.classify_posts_batch(
                        post_uids=batch,
                        session=session,
                        classifier_slugs=classifier_slugs,
                        parallel=True
                    )
                    
                    processed += len(batch)
                    classified = result.get("total_classified", 0)
                    skipped = result.get("total_skipped", 0) 
                    errors = result.get("errors", [])
                    
                    # Update job progress
                    update_job_progress(
                        job_id=job_id,
                        processed=processed,
                        classified=classified,
                        skipped=skipped,
                        errors=errors
                    )
                    
                    # Small delay between batches to avoid overload
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error processing batch in job {job_id}", error=str(e))
                    update_job_progress(
                        job_id=job_id,
                        processed=processed,
                        errors=[f"Batch error: {str(e)}"]
                    )
            
            logger.info(f"Completed batch classification job {job_id}")
            
        except Exception as e:
            logger.error(f"Fatal error in batch classification job {job_id}", error=str(e))
            if job_id in _jobs:
                _jobs[job_id]["status"] = "failed"
                _jobs[job_id]["errors"].append(f"Fatal error: {str(e)}")
                _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()