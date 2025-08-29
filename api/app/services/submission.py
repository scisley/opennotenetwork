"""
Submission service for sending notes to X.com and reconciling outcomes
"""
import structlog
from requests_oauthlib import OAuth1Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Dict, Any, List
import uuid
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential

from app.models import DraftNote, Submission, Post
from app.config import settings

logger = structlog.get_logger()


class XSubmissionClient:
    """Client for submitting Community Notes to X.com"""
    
    def __init__(self):
        self.oauth = OAuth1Session(
            client_key=settings.x_api_key,
            client_secret=settings.x_api_key_secret,
            resource_owner_key=settings.x_access_token,
            resource_owner_secret=settings.x_access_token_secret,
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def submit_note(
        self,
        platform_post_id: str,
        note_text: str,
        classification: str = "misinformed_or_potentially_misleading",
        misleading_tags: List[str] = None
    ) -> Dict[str, Any]:
        """Submit a Community Note to X.com"""
        
        if misleading_tags is None:
            misleading_tags = ["missing_important_context"]
        
        payload = {
            "test_mode": True,  # Required for now per API docs
            "post_id": platform_post_id,
            "info": {
                "text": note_text,
                "classification": classification,
                "misleading_tags": misleading_tags,
                "trustworthy_sources": True
            }
        }
        
        try:
            logger.info(
                "Submitting note to X.com",
                post_id=platform_post_id,
                note_length=len(note_text)
            )
            
            response = self.oauth.post(
                "https://api.x.com/2/notes",
                json=payload
            )
            
            if response.status_code != 201:
                error_data = response.json() if response.content else {}
                raise Exception(f"X API returned {response.status_code}: {error_data}")
            
            result = response.json()
            
            logger.info(
                "Note submitted successfully",
                post_id=platform_post_id,
                note_id=result.get("data", {}).get("note_id")
            )
            
            return result
            
        except Exception as e:
            logger.error("Failed to submit note to X.com", error=str(e))
            raise
    
    async def get_note_status(self, note_id: str) -> Dict[str, Any]:
        """Get the status of a submitted note (stub for now)"""
        # TODO: X.com doesn't currently provide a public API to check note status
        # This would need to be implemented when that API becomes available
        
        logger.info("Checking note status (stub)", note_id=note_id)
        
        # Return mock status for now
        return {
            "note_id": note_id,
            "status": "submitted",  # Could be: submitted, accepted, rejected, unknown
            "decision_time": None
        }


async def submit(
    draft_id: str,
    submitted_by: uuid.UUID,
    session: AsyncSession
) -> Dict[str, Any]:
    """
    Submit an approved draft to X.com
    
    This function is idempotent - calling it multiple times with the same
    draft_id will return the existing submission.
    """
    try:
        # Check if already submitted
        existing_result = await session.execute(
            select(Submission)
            .where(Submission.draft_id == uuid.UUID(draft_id))
        )
        existing_submission = existing_result.scalar_one_or_none()
        
        if existing_submission:
            logger.info(
                "Draft already submitted, returning existing submission",
                draft_id=draft_id,
                submission_id=str(existing_submission.submission_id)
            )
            return {
                "submission_id": str(existing_submission.submission_id),
                "x_note_id": existing_submission.x_note_id,
                "status": existing_submission.submission_status
            }
        
        # Get the draft and related post
        draft_result = await session.execute(
            select(DraftNote, Post)
            .join(Post, DraftNote.post_uid == Post.post_uid)
            .where(DraftNote.draft_id == uuid.UUID(draft_id))
        )
        draft_row = draft_result.first()
        
        if not draft_row:
            raise ValueError(f"Draft not found: {draft_id}")
        
        draft, post = draft_row
        
        # Validate draft is approved
        if draft.draft_status != "approved":
            raise ValueError(f"Draft must be approved before submission, current status: {draft.draft_status}")
        
        # Validate concise note constraints
        from app.services.validation import validate_concise_note
        is_valid, errors = await validate_concise_note(draft.concise_body)
        if not is_valid:
            raise ValueError(f"Concise note validation failed: {errors}")
        
        # Submit to X.com
        client = XSubmissionClient()
        x_response = await client.submit_note(
            platform_post_id=post.platform_post_id,
            note_text=draft.concise_body
        )
        
        # Extract note ID from response
        x_note_id = x_response.get("data", {}).get("note_id")
        
        # Create submission record
        submission = Submission(
            post_uid=post.post_uid,
            draft_id=draft.draft_id,
            x_note_id=x_note_id,
            submission_status="submitted",
            submitted_by=submitted_by,
            response_json=x_response
        )
        
        # Update draft status
        await session.execute(
            update(DraftNote)
            .where(DraftNote.draft_id == draft.draft_id)
            .values(draft_status="submitted")
        )
        
        session.add(submission)
        await session.commit()
        
        logger.info(
            "Submission completed successfully",
            draft_id=draft_id,
            submission_id=str(submission.submission_id),
            x_note_id=x_note_id
        )
        
        return {
            "submission_id": str(submission.submission_id),
            "x_note_id": x_note_id,
            "status": "submitted"
        }
        
    except Exception as e:
        await session.rollback()
        logger.error("Submission failed", draft_id=draft_id, error=str(e))
        raise


async def reconcile(session: AsyncSession) -> Dict[str, Any]:
    """
    Reconcile submission outcomes by checking X.com for status updates
    """
    checked = 0
    updated = 0
    unchanged = 0
    
    try:
        # Get pending submissions (submitted or unknown status)
        pending_result = await session.execute(
            select(Submission)
            .where(Submission.submission_status.in_(["submitted", "unknown"]))
            .order_by(Submission.submitted_at.desc())
        )
        pending_submissions = pending_result.scalars().all()
        
        client = XSubmissionClient()
        
        for submission in pending_submissions:
            checked += 1
            
            try:
                if submission.x_note_id:
                    # Check status with X.com
                    status_data = await client.get_note_status(submission.x_note_id)
                    new_status = status_data.get("status", "unknown")
                    
                    if new_status != submission.submission_status:
                        # Update submission status
                        await session.execute(
                            update(Submission)
                            .where(Submission.submission_id == submission.submission_id)
                            .values(
                                submission_status=new_status,
                                response_json=status_data
                            )
                        )
                        updated += 1
                        
                        logger.info(
                            "Updated submission status",
                            submission_id=str(submission.submission_id),
                            old_status=submission.submission_status,
                            new_status=new_status
                        )
                    else:
                        unchanged += 1
                else:
                    # No X note ID available, mark as unknown
                    if submission.submission_status != "unknown":
                        await session.execute(
                            update(Submission)
                            .where(Submission.submission_id == submission.submission_id)
                            .values(submission_status="unknown")
                        )
                        updated += 1
                    else:
                        unchanged += 1
                        
            except Exception as e:
                logger.error(
                    "Failed to reconcile submission",
                    submission_id=str(submission.submission_id),
                    error=str(e)
                )
                unchanged += 1
        
        await session.commit()
        
        logger.info(
            "Reconciliation completed",
            checked=checked,
            updated=updated,
            unchanged=unchanged
        )
        
        return {
            "checked": checked,
            "updated": updated,
            "unchanged": unchanged
        }
        
    except Exception as e:
        await session.rollback()
        logger.error("Reconciliation failed", error=str(e))
        raise


async def get_submission_stats(session: AsyncSession) -> Dict[str, Any]:
    """Get submission and outcome statistics"""
    from sqlalchemy import func
    
    # Count total submissions
    total_result = await session.execute(
        select(func.count(Submission.submission_id))
    )
    total_submissions = total_result.scalar()
    
    # Count by status
    status_result = await session.execute(
        select(Submission.submission_status, func.count(Submission.submission_id))
        .group_by(Submission.submission_status)
    )
    by_status = dict(status_result.fetchall())
    
    # Count submissions in last 24 hours
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_result = await session.execute(
        select(func.count(Submission.submission_id))
        .where(Submission.submitted_at >= since)
    )
    recent_submissions = recent_result.scalar()
    
    # Calculate acceptance rate
    accepted = by_status.get("accepted", 0)
    acceptance_rate = (accepted / total_submissions * 100) if total_submissions > 0 else 0
    
    return {
        "total_submissions": total_submissions,
        "by_status": by_status,
        "recent_24h": recent_submissions,
        "acceptance_rate": round(acceptance_rate, 2)
    }