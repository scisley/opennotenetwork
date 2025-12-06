"""
Note Writing Service

Handles running note writers on fact checks and managing results.
"""

import uuid
from typing import Any

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import FactCheck, Note, NoteWriter, Submission
from app.note_writers import NoteWriterRegistry
from app.database import async_session_factory

logger = structlog.get_logger()


def _build_note_response(note, note_writer=None, submission=None) -> dict[str, Any]:
    """Build a standardized note response"""
    response = {
        "note_id": str(note.note_id),
        "fact_check_id": str(note.fact_check_id),
        "note_writer_id": str(note.note_writer_id),
        "status": note.status,
        "text": note.text,
        "links": note.links,
        "submission_json": note.submission_json,
        "evaluation_json": note.evaluation_json,
        "created_at": note.created_at.isoformat(),
        "is_edited": note.is_edited,
        "original_text": note.original_text,
        "original_links": note.original_links
    }

    if hasattr(note, 'error_message') and note.error_message:
        response["error_message"] = note.error_message

    if hasattr(note, 'updated_at') and note.updated_at:
        response["updated_at"] = note.updated_at.isoformat()

    if note_writer:
        response["note_writer"] = {
            "slug": note_writer.slug,
            "name": note_writer.name,
        }
        if hasattr(note_writer, 'version'):
            response["note_writer"]["version"] = note_writer.version
    
    if submission:
        response["submission"] = {
            "submission_id": str(submission.submission_id),
            "status": submission.status,
            "x_note_id": submission.x_note_id,
            "submitted_at": submission.submitted_at.isoformat()
        }

    return response


async def write_note(
    fact_check_id: str,
    note_writer_slug: str,
    force: bool = False
) -> dict[str, Any]:
    """
    Run a specific note writer on a fact check

    Args:
        fact_check_id: The fact check to write a note for
        note_writer_slug: The note writer to use
        force: If True, rerun even if a result exists

    Returns:
        Dict with note result
    """
    # Create our own session for this operation
    async with async_session_factory() as session:
        # Get the fact check with post data
        result = await session.execute(
            select(FactCheck)
            .options(selectinload(FactCheck.post))
            .where(FactCheck.fact_check_id == uuid.UUID(fact_check_id))
        )
        fact_check = result.scalar_one_or_none()

        if not fact_check:
            raise ValueError(f"Fact check {fact_check_id} not found")

        if fact_check.status != "completed":
            raise ValueError(f"Fact check {fact_check_id} is not completed (status: {fact_check.status})")

        # Get note writer record from database
        result = await session.execute(
            select(NoteWriter).where(NoteWriter.slug == note_writer_slug)
        )
        note_writer_record = result.scalar_one_or_none()

        if not note_writer_record:
            raise ValueError(f"Note writer {note_writer_slug} not found in database")

        # Check if platform is supported
        post = fact_check.post
        if post.platform not in note_writer_record.platforms:
            raise ValueError(f"Note writer {note_writer_slug} does not support platform {post.platform}")

        # Check if we already have a result
        if not force:
            result = await session.execute(
                select(Note).where(
                    and_(
                        Note.fact_check_id == uuid.UUID(fact_check_id),
                        Note.note_writer_id == note_writer_record.note_writer_id,
                        Note.status == "completed"
                    )
                )
            )
            existing_note = result.scalar_one_or_none()

            if existing_note:
                logger.info(f"Returning existing note for fact check {fact_check_id} with {note_writer_slug}")
                return _build_note_response(existing_note, note_writer_record)

        # Delete any existing note if forcing
        if force:
            delete_result = await session.execute(
                select(Note).where(
                    and_(
                        Note.fact_check_id == uuid.UUID(fact_check_id),
                        Note.note_writer_id == note_writer_record.note_writer_id
                    )
                )
            )
            existing = delete_result.scalar_one_or_none()
            if existing:
                await session.delete(existing)
                await session.flush()

        # Prepare post data for the note writer
        post_data = {
            "post_uid": post.post_uid,
            "text": post.text,
            "author_handle": post.author_handle,
            "platform": post.platform,
            "raw_json": post.raw_json
        }

        # Prepare fact check data for the note writer
        fact_check_data = {
            "body": fact_check.body or "",
            "verdict": fact_check.verdict,
            "confidence": fact_check.confidence,
            "fact_check_id": str(fact_check.fact_check_id),
            "status": fact_check.status
        }

        # Get the note writer instance and run it
        note_writer_instance = NoteWriterRegistry.get_instance(note_writer_slug)
        if not note_writer_instance:
            raise ValueError(f"Note writer {note_writer_slug} not found")

        try:
            # Run the note writer
            logger.info(f"Running note writer {note_writer_slug} for fact check {fact_check_id}")
            result = await note_writer_instance.write_note(post_data, fact_check_data)

            # Extract evaluation from metadata if present
            evaluation_json = None
            if result.metadata and "evaluation" in result.metadata:
                evaluation_json = result.metadata["evaluation"]

            # Create note record with completed status
            note = Note(
                fact_check_id=uuid.UUID(fact_check_id),
                note_writer_id=note_writer_record.note_writer_id,
                text=result.text,
                links=result.links,
                raw_json=result.raw_output if result.raw_output else {
                    "metadata": result.metadata,
                    "version": result.version
                },
                submission_json=result.submission_json,
                evaluation_json=evaluation_json,
                status="completed"
            )
            session.add(note)
            await session.commit()

            logger.info(f"Note completed for fact check {fact_check_id} with {note_writer_slug}")

            # Auto-submit if score qualifies (hardcoded threshold: -0.5)
            if evaluation_json and not evaluation_json.get("error"):
                score = evaluation_json.get("data", {}).get("claim_opinion_score")
                if score is not None and score > -0.5:
                    try:
                        logger.info(f"Auto-submitting note {note.note_id} with score {score}")

                        # Import here to avoid circular dependency
                        from app.services import submission
                        await submission.submit_note_to_x(
                            note_id=note.note_id,
                            session=session,
                            # Steve Isley's user ID
                            submitted_by_id=uuid.UUID("fe683772-7747-4479-9bdd-b80aa90cfee9")
                        )

                        logger.info(f"Successfully auto-submitted note {note.note_id}")
                    except Exception as e:
                        logger.warning(f"Auto-submit failed for note {note.note_id}: {e}")
                        # Continue gracefully - note is still created successfully

            return _build_note_response(note, note_writer_record)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in note writer: {error_msg}",
                        fact_check_id=fact_check_id,
                        note_writer=note_writer_slug)

            # Create failed note record
            note = Note(
                fact_check_id=uuid.UUID(fact_check_id),
                note_writer_id=note_writer_record.note_writer_id,
                status="failed",
                error_message=error_msg
            )
            session.add(note)
            await session.commit()

            return _build_note_response(note, note_writer_record)


async def get_notes_for_fact_check(
    fact_check_id: str
) -> list[dict[str, Any]]:
    """
    Get all notes for a fact check

    Args:
        fact_check_id: The fact check to get notes for

    Returns:
        List of note results
    """
    # Get notes with writers using a fresh session
    async with async_session_factory() as session:
        result = await session.execute(
            select(Note, NoteWriter)
            .join(NoteWriter)
            .where(Note.fact_check_id == uuid.UUID(fact_check_id))
            .order_by(Note.created_at.desc())
        )
        notes_with_writers = list(result)
        
        # Get submissions for these notes
        note_ids = [note.note_id for note, _ in notes_with_writers]
        if note_ids:
            submission_result = await session.execute(
                select(Submission)
                .where(Submission.note_id.in_(note_ids))
                .where(Submission.status != "submission_failed")
            )
            submissions_by_note = {
                sub.note_id: sub for sub in submission_result.scalars()
            }
        else:
            submissions_by_note = {}

    return [
        _build_note_response(note, note_writer, submissions_by_note.get(note.note_id))
        for note, note_writer in notes_with_writers
    ]


async def list_available_note_writers() -> list[dict[str, Any]]:
    """
    List all available note writers from the database

    Returns:
        List of note writer information
    """
    
    # Get all active note writers from database
    async with async_session_factory() as session:
        result = await session.execute(
            select(NoteWriter)
            .where(NoteWriter.is_active == True)
            .order_by(NoteWriter.name)
        )
        writers = result.scalars().all()

        # Convert to response format
        return [
        {
            "id": str(writer.note_writer_id),
            "slug": writer.slug,
            "name": writer.name,
            "description": writer.description,
            "version": writer.version,
            "platforms": writer.platforms,
            "is_active": writer.is_active,
            "created_at": writer.created_at.isoformat(),
            "updated_at": writer.updated_at.isoformat() if writer.updated_at else None
        }
        for writer in writers
    ]


async def auto_write_notes_for_fact_check(
    fact_check_id: str,
    platform: str
) -> list[dict[str, Any]]:
    """
    Automatically write notes using all active note writers for a platform

    Args:
        fact_check_id: The fact check to write notes for
        platform: The platform the post is from

    Returns:
        List of note results
    """
    # Get all active note writers for this platform from database
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(NoteWriter)
            .where(
                NoteWriter.is_active == True,
                NoteWriter.platforms.contains([platform])
            )
        )
        writers = result.scalars().all()

    results = []
    for writer in writers:
        try:
            result = await write_note(
                fact_check_id=fact_check_id,
                note_writer_slug=writer.slug,
                force=False  # Don't force, skip if already exists
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to auto-write note with {writer.slug}: {e}",
                        fact_check_id=fact_check_id)
            # Continue with other writers

    return results
