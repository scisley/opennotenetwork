"""
Service for submitting Community Notes to X.com and tracking their status
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone
from typing import Dict, Any
import json
import uuid
import requests
from requests_oauthlib import OAuth1

from app.models import Submission, Note
from app.config import settings

logger = structlog.get_logger()


async def submit_note_to_x(
    note_id: uuid.UUID,
    session: AsyncSession,
    submitted_by_id: uuid.UUID
) -> Dict[str, Any]:
    """
    Submit a single note to X.com Community Notes API

    Returns dict with submission_id and status
    """
    # Get the note
    result = await session.execute(
        select(Note)
        .where(Note.note_id == note_id)
    )
    note = result.scalar_one()

    # Use the submission_json from the note (already prepared by note writer)
    submission_data = note.submission_json.copy()  # Copy to avoid modifying the original

    # Add test_mode flag (required by X API)
    submission_data["test_mode"] = False

    # For not_misleading, misleading_tags must be absent.
    if submission_data["info"].get("classification") == "not_misleading":
        print("INFO is not_misleading")
        submission_data["info"].pop("misleading_tags", None)

    submission_data["info"]["text"] = clean_text(submission_data["info"]["text"])
    
    # Create submission record first (in pending state)
    submission = Submission(
        note_id=note.note_id,
        submitted_by=submitted_by_id,
        note_writer_id=note.note_writer_id,
        submission_json=submission_data,
        status="pending"
    )
    session.add(submission)
    await session.flush()
    
    # Create OAuth1 auth
    auth = OAuth1(
        settings.x_api_key,
        client_secret=settings.x_api_key_secret,
        resource_owner_key=settings.x_access_token,
        resource_owner_secret=settings.x_access_token_secret
    )

    logger.info(
        "Submitting note to X",
        note_id=str(note_id),
        submission_data=json.dumps(submission_data),
    )

    # Make the API call
    response = requests.post(
        "https://api.twitter.com/2/notes",
        json=submission_data,
        auth=auth,
        headers={"Content-Type": "application/json"},
        timeout=30 
    )

    if not response.ok:
        # Submission failed
        submission.status = "submission_failed"

        # Try to parse JSON error response
        error_message = response.text
        try:
            error_data = response.json()
            submission.submission_errors = error_data
            # Example error data: {'detail': 'Failed to create a note. You’ve reached your daily limit for writing notes.', 'type': 'about:blank', 'title': 'Forbidden', 'status': 403}

            # Extract user-friendly error message
            if response.status_code == 403 and "daily limit" in error_data.get("detail", "").lower():
                error_message = "Daily note submission limit reached. You cannot submit more notes today."
            elif "detail" in error_data:
                error_message = error_data["detail"]
            elif "message" in error_data:
                error_message = error_data["message"]
        except (json.JSONDecodeError, ValueError):
            # If JSON parsing fails, use raw text
            submission.submission_errors = {
                "error": response.text,
                "status_code": response.status_code
            }

        await session.commit()

        logger.error(
            "Failed to submit note",
            note_id=str(note_id),
            status_code=response.status_code,
            response=response.text
        )

        return {
            "submission_id": str(submission.submission_id),
            "status": "submission_failed",
            "x_note_id": None,
            "error": error_message
        }

    # Parse response
    response_data = response.json()

    # Log the full response for debugging
    logger.info(
        "X.com API response received",
        note_id=str(note_id),
        response=response_data
    )

    submission.response_json = response_data
    submission.status = "submitted"
    
    # Extract X note ID if provided
    if "data" in response_data and "id" in response_data["data"]:
        submission.x_note_id = response_data["data"]["id"]
    
    await session.commit()
    
    logger.info(
        "Successfully submitted note",
        note_id=str(note_id),
        x_note_id=submission.x_note_id
    )
    
    return {
        "submission_id": str(submission.submission_id),
        "status": "submitted",
        "x_note_id": submission.x_note_id,
        "error": None
    }


async def update_submission_statuses(
    session: AsyncSession
) -> Dict[str, Any]:
    """
    Fetch all notes from X API and update submission statuses

    Returns summary of updates
    """
    updated_count = 0
    error_count = 0
    errors = []
    
    # Create OAuth1 auth
    auth = OAuth1(
        settings.x_api_key,
        client_secret=settings.x_api_key_secret,
        resource_owner_key=settings.x_access_token,
        resource_owner_secret=settings.x_access_token_secret
    )

    # Fetch all notes from X API
    pagination_token = None
    all_x_notes = []

    while True:
        params = {
            "max_results": 100,
            "note.fields": "id,info,status",
            "test_mode": "false"
        }

        if pagination_token:
            params["pagination_token"] = pagination_token

        logger.info("Fetching notes from X", has_token=bool(pagination_token))

        response = requests.get(
            "https://api.twitter.com/2/notes/search/notes_written",
            params=params,
            auth=auth,
            headers={"Content-Type": "application/json"}
        )

        if not response.ok:
            error_msg = f"Failed to fetch notes: {response.text}"
            logger.error("API request failed",
                        status_code=response.status_code,
                        response=response.text[:500])
            errors.append(error_msg)
            break

        data = response.json()
        notes = data.get("data", [])
        all_x_notes.extend(notes)

        logger.info("Fetched batch from X",
                   count=len(notes),
                   has_data="data" in data,
                   response_keys=list(data.keys()))

        # Check for more pages
        pagination_token = data.get("meta", {}).get("next_token")
        if not pagination_token:
            break
    
    logger.info(f"Fetched {len(all_x_notes)} notes from X")
    
    # Create lookup by x_note_id
    x_notes_by_id = {note["id"]: note for note in all_x_notes}
    
    # Get all submitted submissions
    result = await session.execute(
        select(Submission)
        .where(Submission.status.in_(["submitted", "displayed", "not_displayed"]))
    )
    submissions = result.scalars().all()
    
    # Update all submissions in memory first
    current_time = datetime.now(timezone.utc)

    for submission in submissions:
        if not submission.x_note_id:
            continue

        x_note = x_notes_by_id.get(submission.x_note_id)
        if not x_note:
            continue

        # Check if status_json actually changed (compare old vs new)
        old_status_json = submission.status_json
        status_changed = old_status_json != x_note

        # Update status_json
        submission.status_json = x_note

        # Only update status_updated_at if status_json actually changed
        if status_changed:
            submission.status_updated_at = current_time

        # Map X status to our status
        x_status = x_note.get("status", "").lower()
        if "currently_rated_helpful" in x_status:
            submission.status = "displayed"
        elif any(s in x_status for s in ["currently_rated_not_helpful", "firm_reject",
                                          "insufficient_consensus", "minimum_ratings_not_met"]):
            submission.status = "not_displayed"
        # Keep as "submitted" for notes still being evaluated
        # (needs_more_ratings, needs_your_help, etc.)

        updated_count += 1
    
    # Commit all changes at once
    await session.commit()
    
    logger.info(
        "Status update complete",
        updated=updated_count,
        errors=error_count,
        total_x_notes=len(all_x_notes)
    )
    
    return {
        "updated_count": updated_count,
        "error_count": error_count,
        "errors": errors,
        "total_x_notes": len(all_x_notes),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


async def get_submissions_summary(session: AsyncSession) -> Dict[str, Any]:
    """
    Get summary statistics for submissions
    """
    # Count by status
    status_counts = {}
    for status in ["pending", "submitted", "submission_failed", "displayed", "not_displayed", "deleted"]:
        result = await session.execute(
            select(Submission)
            .where(Submission.status == status)
        )
        status_counts[status] = len(result.scalars().all())

    # Get last update time
    result = await session.execute(
        select(Submission)
        .where(Submission.status_updated_at.isnot(None))
        .order_by(Submission.status_updated_at.desc())
        .limit(1)
    )
    last_submission = result.scalar_one_or_none()

    return {
        "status_counts": status_counts,
        "total": sum(status_counts.values()),
        "last_status_update": last_submission.status_updated_at.isoformat() if last_submission else None
    }


async def calculate_writing_limit(session: AsyncSession) -> Dict[str, Any]:
    """
    Calculate X.com daily writing limit based on submission history

    Implements X.com's writing limit algorithm:
    - WL = Daily writing limit
    - NH_5 = Not helpful in last 5 non-NMR notes
    - NH_10 = Not helpful in last 10 non-NMR notes
    - HR_R = Recent hit rate (last 20 notes)
    - HR_L = Long-term hit rate (last 100 notes)
    - DN_30 = Average daily notes in last 30 days
    - T = Total notes written
    """
    from datetime import timedelta

    # Get all submitted notes ordered by submitted_at DESC
    result = await session.execute(
        select(Submission)
        .where(Submission.status.in_(["submitted", "displayed", "not_displayed"]))
        .order_by(Submission.submitted_at.desc())
    )
    submissions = result.scalars().all()

    # Filter to only notes with X status (exclude pending status updates)
    notes_with_status = [s for s in submissions if s.status_json and s.status_json.get("status")]
    notes_without_status = len(submissions) - len(notes_with_status)

    # Helper functions to check X status
    def is_crnh(sub):
        """Currently Rated Not Helpful"""
        status = sub.status_json.get("status", "").lower()
        return "currently_rated_not_helpful" in status

    def is_crh(sub):
        """Currently Rated Helpful"""
        status = sub.status_json.get("status", "").lower()
        return "currently_rated_helpful" in status

    def is_nmr(sub):
        """Needs More Ratings"""
        status = sub.status_json.get("status", "").lower()
        return "needs_more_ratings" in status

    # Get non-NMR notes for NH_5 and NH_10
    non_nmr_notes = [s for s in notes_with_status if not is_nmr(s)]

    # Calculate NH_5 and NH_10
    nh_5 = sum(1 for s in non_nmr_notes[:5] if is_crnh(s))
    nh_10 = sum(1 for s in non_nmr_notes[:10] if is_crnh(s))

    # Calculate HR_R (recent hit rate - last 20 notes)
    recent_20 = notes_with_status[:20]
    if recent_20:
        crh_count = sum(1 for s in recent_20 if is_crh(s))
        crnh_count = sum(1 for s in recent_20 if is_crnh(s))
        hr_r = (crh_count - crnh_count) / len(recent_20)
    else:
        hr_r = 0.0

    # Calculate HR_L (long-term hit rate - last 100 notes)
    long_100 = notes_with_status[:100]
    if long_100:
        crh_count = sum(1 for s in long_100 if is_crh(s))
        crnh_count = sum(1 for s in long_100 if is_crnh(s))
        hr_l = (crh_count - crnh_count) / len(long_100)
    else:
        hr_l = 0.0

    # Calculate DN_30 (average daily notes in last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_notes = [s for s in notes_with_status if s.submitted_at and s.submitted_at >= thirty_days_ago]
    dn_30 = len(recent_notes) / 30.0

    # Calculate T (total notes)
    total_notes = len(notes_with_status)

    # Apply X.com's writing limit algorithm
    if nh_10 >= 8:
        wl = 2
    elif nh_5 >= 3:
        wl = 5
    else:
        if total_notes < 20:
            wl = 10
        else:
            wl = max(5, int(min(dn_30 * 5, 200 * max(hr_r, hr_l))))

    return {
        "writing_limit": wl,
        "nh_5": nh_5,
        "nh_10": nh_10,
        "hr_r": hr_r,
        "hr_l": hr_l,
        "dn_30": dn_30,
        "total_notes": total_notes,
        "notes_without_status": notes_without_status,
        "calculated_at": datetime.now(timezone.utc).isoformat()
    }

def clean_text(text: str) -> str:
    replacements = {
        "\u2011": "-",   # non-breaking hyphen → regular hyphen
        "\u2013": "-",   # en dash → hyphen
        "\u2014": "-",   # em dash → hyphen
        "\u2018": "'",   # left single quote → apostrophe
        "\u2019": "'",   # right single quote → apostrophe
        "\u201c": '"',   # left double quote → quotation mark
        "\u201d": '"',   # right double quote → quotation mark
        "\u2026": "...", # ellipsis → three dots
    }
    
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text