"""
Fact Checking Service

Handles running fact checkers on posts and managing results.
"""

import uuid
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
import structlog

from app.models import Post, FactChecker, FactCheck, Classification
from app.fact_checkers import FactCheckerRegistry
from app.database import parse_post_uid, get_session

logger = structlog.get_logger()


async def _run_fact_check_background(
    fact_check_id: str,
    fact_checker_slug: str,
    post_data: Dict[str, Any]
) -> None:
    """
    Background task to run a fact checker and update the database
    
    Args:
        fact_check_id: ID of the fact check record to update
        fact_checker_slug: The fact checker to run
        post_data: Post data to check
    """
    # Create a new database session for this background task
    async for session in get_session():
        try:
            # Update status to processing
            await session.execute(
                update(FactCheck)
                .where(FactCheck.id == uuid.UUID(fact_check_id))
                .values(
                    status="processing",
                    check_metadata={"started_at": datetime.utcnow().isoformat()}
                )
            )
            await session.commit()
            
            # Get the fact checker instance
            fact_checker = FactCheckerRegistry.get_instance(fact_checker_slug)
            if not fact_checker:
                raise ValueError(f"Fact checker {fact_checker_slug} not found")
            
            # Run the fact checker
            logger.info(f"Running fact checker {fact_checker_slug} in background", 
                       fact_check_id=fact_check_id)
            result = await fact_checker.fact_check(post_data)
            
            # Update the fact check record with results
            await session.execute(
                update(FactCheck)
                .where(FactCheck.id == uuid.UUID(fact_check_id))
                .values(
                    status="completed",
                    result={
                        "text": result.text,
                        "claims": result.claims,
                        "sources": result.sources,
                        "version": result.version
                    },
                    verdict=result.verdict,
                    confidence=result.confidence,
                    check_metadata={
                        **(result.metadata or {}),
                        "completed_at": datetime.utcnow().isoformat()
                    }
                )
            )
            await session.commit()
            
            logger.info(f"Fact check completed in background", 
                       fact_check_id=fact_check_id,
                       verdict=result.verdict)
            
        except Exception as e:
            logger.error(f"Error in background fact checker: {str(e)}", 
                        fact_check_id=fact_check_id,
                        fact_checker=fact_checker_slug)
            
            # Update fact check record with error
            try:
                await session.execute(
                    update(FactCheck)
                    .where(FactCheck.id == uuid.UUID(fact_check_id))
                    .values(
                        status="failed",
                        error_message=str(e),
                        check_metadata={
                            "failed_at": datetime.utcnow().isoformat(),
                            "error": str(e)
                        }
                    )
                )
                await session.commit()
            except Exception as update_error:
                logger.error(f"Failed to update error status: {str(update_error)}", 
                           fact_check_id=fact_check_id)
        finally:
            await session.close()


async def run_fact_check(
    post_uid: str,
    fact_checker_slug: str,
    session: AsyncSession,
    force: bool = False
) -> Dict[str, Any]:
    """
    Run a specific fact checker on a post
    
    Args:
        post_uid: The post to check
        fact_checker_slug: The fact checker to use
        session: Database session
        force: If True, rerun even if a result exists
    
    Returns:
        Dict with fact check result
    """
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
                    FactCheck.fact_checker_id == fact_checker_record.id,
                    FactCheck.status == "completed"
                )
            )
        )
        existing_check = result.scalar_one_or_none()
        
        if existing_check:
            logger.info(f"Returning existing fact check for {post_uid} with {fact_checker_slug}")
            return {
                "id": str(existing_check.id),
                "status": existing_check.status,
                "result": existing_check.result,
                "verdict": existing_check.verdict,
                "confidence": float(existing_check.confidence) if existing_check.confidence else None,
                "created_at": existing_check.created_at.isoformat()
            }
    
    # Delete any existing check if forcing
    if force:
        delete_result = await session.execute(
            select(FactCheck).where(
                and_(
                    FactCheck.post_uid == post_uid,
                    FactCheck.fact_checker_id == fact_checker_record.id
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
        fact_checker_id=fact_checker_record.id,
        status="pending",
        result={},
        check_metadata={"started_at": datetime.utcnow().isoformat()}
    )
    session.add(fact_check)
    await session.commit()  # Commit immediately so the record exists
    
    fact_check_id = str(fact_check.id)
    
    # Prepare post data for the background task
    post_data = {
        "post_uid": post.post_uid,
        "text": post.text,
        "author_handle": post.author_handle,
        "platform": post.platform,
        "raw_json": post.raw_json,
        "classifications": []
    }
    
    # Add classification data if available
    if post.classifications:
        for classification in post.classifications:
            post_data["classifications"].append({
                "classifier_slug": classification.classifier_slug,
                "classification_data": classification.classification_data
            })
    
    # Launch background task to run the fact checker
    import asyncio
    asyncio.create_task(
        _run_fact_check_background(
            fact_check_id=fact_check_id,
            fact_checker_slug=fact_checker_slug,
            post_data=post_data
        )
    )
    
    logger.info(f"Fact check job started for {post_uid} with {fact_checker_slug}")
    
    # Return immediately with pending status
    return {
        "id": fact_check_id,
        "status": "pending",
        "result": None,
        "verdict": None,
        "confidence": None,
        "created_at": fact_check.created_at.isoformat()
    }


async def get_fact_checks_for_post(
    post_uid: str,
    session: AsyncSession
) -> List[Dict[str, Any]]:
    """
    Get all fact checks for a post
    
    Args:
        post_uid: The post to get fact checks for
        session: Database session
    
    Returns:
        List of fact check results
    """
    result = await session.execute(
        select(FactCheck, FactChecker)
        .join(FactChecker)
        .where(FactCheck.post_uid == post_uid)
        .order_by(FactCheck.created_at.desc())
    )
    
    fact_checks = []
    for fact_check, fact_checker in result:
        fact_checks.append({
            "id": str(fact_check.id),
            "fact_checker": {
                "slug": fact_checker.slug,
                "name": fact_checker.name,
                "version": fact_checker.version
            },
            "status": fact_check.status,
            "result": fact_check.result,
            "verdict": fact_check.verdict,
            "confidence": float(fact_check.confidence) if fact_check.confidence else None,
            "error_message": fact_check.error_message,
            "created_at": fact_check.created_at.isoformat(),
            "updated_at": fact_check.updated_at.isoformat()
        })
    
    return fact_checks


async def get_fact_check_status(
    fact_check_id: str,
    session: AsyncSession
) -> Optional[Dict[str, Any]]:
    """
    Get the status of a fact check job
    
    Args:
        fact_check_id: The fact check ID
        session: Database session
    
    Returns:
        Status information or None if not found
    """
    try:
        check_uuid = uuid.UUID(fact_check_id)
    except ValueError:
        return None
    
    result = await session.execute(
        select(FactCheck, FactChecker)
        .join(FactChecker)
        .where(FactCheck.id == check_uuid)
    )
    
    row = result.first()
    if not row:
        return None
    
    fact_check, fact_checker = row
    
    return {
        "id": str(fact_check.id),
        "post_uid": fact_check.post_uid,
        "fact_checker": {
            "slug": fact_checker.slug,
            "name": fact_checker.name
        },
        "status": fact_check.status,
        "result": fact_check.result if fact_check.status == "completed" else None,
        "verdict": fact_check.verdict,
        "confidence": float(fact_check.confidence) if fact_check.confidence else None,
        "error_message": fact_check.error_message,
        "created_at": fact_check.created_at.isoformat(),
        "updated_at": fact_check.updated_at.isoformat()
    }


async def list_available_fact_checkers(session: AsyncSession) -> List[Dict[str, Any]]:
    """
    List all available fact checkers
    
    Args:
        session: Database session
    
    Returns:
        List of fact checker information
    """
    # Get from registry
    registry_checkers = FactCheckerRegistry.list_all()
    
    # Get from database
    result = await session.execute(
        select(FactChecker).where(FactChecker.is_active == True)
    )
    db_checkers = result.scalars().all()
    
    # Merge information
    checkers = {}
    
    # Start with registry
    for checker in registry_checkers:
        checkers[checker["slug"]] = {
            **checker,
            "available": True,
            "in_database": False
        }
    
    # Add database info
    for checker in db_checkers:
        if checker.slug in checkers:
            checkers[checker.slug]["in_database"] = True
            checkers[checker.slug]["id"] = str(checker.id)
        else:
            # Checker in DB but not in registry
            checkers[checker.slug] = {
                "slug": checker.slug,
                "name": checker.name,
                "description": checker.description,
                "version": checker.version,
                "available": False,
                "in_database": True,
                "id": str(checker.id)
            }
    
    return list(checkers.values())