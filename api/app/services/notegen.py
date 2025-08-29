"""
Note generation service for creating fact-check content using LangGraph agent
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Dict, Any, Optional
import uuid
from datetime import datetime, timezone

from app.models import Post, Topic, DraftNote, PostTopic

logger = structlog.get_logger()

# Current generator version
GENERATOR_VERSION = "langgraph-stub-v1.0"


async def generate(
    post_uid: str,
    session: AsyncSession,
    topic_slug: Optional[str] = None,
    version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a new draft note for a post
    
    Args:
        post_uid: The post to generate a note for
        topic_slug: Optional specific topic to focus on
        session: Database session
        version: Optional generator version
        
    Returns:
        Dict with draft details
    """
    try:
        # Get the post
        result = await session.execute(
            select(Post).where(Post.post_uid == post_uid)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            raise ValueError(f"Post not found: {post_uid}")
        
        # Get topic if specified
        topic = None
        if topic_slug:
            topic_result = await session.execute(
                select(Topic).where(Topic.slug == topic_slug)
            )
            topic = topic_result.scalar_one_or_none()
            if not topic:
                raise ValueError(f"Topic not found: {topic_slug}")
        else:
            # Find the primary topic for this post
            topic_result = await session.execute(
                select(Topic, PostTopic)
                .join(PostTopic)
                .where(PostTopic.post_uid == post_uid)
                .order_by(PostTopic.confidence.desc())
            )
            topic_row = topic_result.first()
            if topic_row:
                topic = topic_row[0]
        
        # Generate the note content
        generator_version = version or GENERATOR_VERSION
        note_content = _create_mock_note_content(post, topic, generator_version)
        
        # Create draft note
        draft_note = DraftNote(
            post_uid=post_uid,
            topic_id=topic.topic_id if topic else None,
            full_body=note_content["full_body"],
            concise_body=note_content["concise_body"],
            citations=note_content.get("citations", []),
            generator_version=generator_version,
            draft_status="draft"
        )
        
        session.add(draft_note)
        await session.commit()
        
        logger.info(
            "Draft generated successfully",
            post_uid=post_uid,
            draft_id=str(draft_note.draft_id),
            topic_slug=topic.slug if topic else None,
            generator_version=generator_version
        )
        
        return {
            "draft_id": str(draft_note.draft_id),
            "post_uid": post_uid,
            "full_body": draft_note.full_body,
            "concise_body": draft_note.concise_body,
            "citations": draft_note.citations,
            "generator_version": generator_version
        }
        
    except Exception as e:
        await session.rollback()
        logger.error("Note generation failed", post_uid=post_uid, error=str(e))
        raise


async def regenerate(
    draft_id: str,
    session: AsyncSession,
    version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Regenerate a draft note, creating a new version and marking the old one as superseded
    """
    try:
        # Get existing draft
        result = await session.execute(
            select(DraftNote).where(DraftNote.draft_id == uuid.UUID(draft_id))
        )
        existing_draft = result.scalar_one_or_none()
        
        if not existing_draft:
            raise ValueError(f"Draft not found: {draft_id}")
        
        # Get the associated post and topic
        post_result = await session.execute(
            select(Post).where(Post.post_uid == existing_draft.post_uid)
        )
        post = post_result.scalar_one()
        
        topic = None
        if existing_draft.topic_id:
            topic_result = await session.execute(
                select(Topic).where(Topic.topic_id == existing_draft.topic_id)
            )
            topic = topic_result.scalar_one_or_none()
        
        # Generate new content
        generator_version = version or GENERATOR_VERSION
        note_content = _create_mock_note_content(post, topic, generator_version)
        
        # Create new draft
        new_draft = DraftNote(
            post_uid=existing_draft.post_uid,
            topic_id=existing_draft.topic_id,
            full_body=note_content["full_body"],
            concise_body=note_content["concise_body"],
            citations=note_content.get("citations", []),
            generator_version=generator_version,
            regenerated_from=existing_draft.draft_id,
            draft_status="draft"
        )
        
        # Mark old draft as superseded
        await session.execute(
            update(DraftNote)
            .where(DraftNote.draft_id == existing_draft.draft_id)
            .values(draft_status="superseded")
        )
        
        session.add(new_draft)
        await session.commit()
        
        logger.info(
            "Draft regenerated successfully",
            old_draft_id=draft_id,
            new_draft_id=str(new_draft.draft_id),
            post_uid=new_draft.post_uid,
            generator_version=generator_version
        )
        
        return {
            "draft_id": str(new_draft.draft_id),
            "post_uid": new_draft.post_uid,
            "full_body": new_draft.full_body,
            "concise_body": new_draft.concise_body,
            "citations": new_draft.citations,
            "generator_version": generator_version
        }
        
    except Exception as e:
        await session.rollback()
        logger.error("Note regeneration failed", draft_id=draft_id, error=str(e))
        raise


def _create_mock_note_content(
    post: Post,
    topic: Optional[Topic],
    generator_version: str
) -> Dict[str, Any]:
    """
    Create mock note content for testing/development
    
    This is a stub implementation. Replace with actual LangGraph logic.
    """
    
    # For now, return stub content
    # TODO: Replace with actual LangGraph API call
    
    platform_post_id = post.platform_post_id
    topic_name = topic.display_name if topic else "General"
    
    # Create mock full fact check
    full_body = f"""# Fact Check: {topic_name} Claim Analysis

## Original Post
The post with ID {platform_post_id} makes claims related to {topic_name.lower()}.

**Post Content:** "{post.text[:200]}{'...' if len(post.text) > 200 else ''}"

## Analysis

### Claim Evaluation
Based on current scientific consensus and credible sources, this claim requires additional context and verification.

### Key Points
- The scientific community maintains that climate change is primarily driven by human activities
- Current data from NASA, NOAA, and the IPCC support the reality of anthropogenic climate change
- Weather patterns and climate trends should be distinguished from each other

### Sources
1. [NASA Climate Change Evidence](https://climate.nasa.gov/evidence/)
2. [NOAA Climate.gov](https://www.climate.gov/)
3. [IPCC Assessment Reports](https://www.ipcc.ch/reports/)

### Conclusion
Additional context is needed to properly evaluate the specific claims made in this post.

---
*Generated by Climate Fact Checker v{generator_version}*"""
    
    # Create mock concise note (must be ≤280 chars with link)
    base_url = "https://your-app.vercel.app"  # TODO: Use actual domain
    note_url = f"{base_url}/notes/{post.post_uid}"
    
    concise_body = f"This claim about {topic_name.lower()} needs additional context. Current scientific consensus from NASA, NOAA & IPCC supports human-caused climate change. See full analysis: {note_url}"
    
    # Ensure concise note is within limits
    if len(concise_body) > 280:
        # Truncate while preserving the URL
        max_text_length = 280 - len(note_url) - 20  # Buffer for "... See: "
        truncated_text = concise_body[:max_text_length] + f"... See: {note_url}"
        concise_body = truncated_text
    
    # Mock citations
    citations = [
        {
            "title": "NASA Climate Change and Global Warming",
            "url": "https://climate.nasa.gov/",
            "source": "NASA",
            "access_date": datetime.now(timezone.utc).isoformat()
        },
        {
            "title": "NOAA Climate.gov",
            "url": "https://www.climate.gov/",
            "source": "NOAA",
            "access_date": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    logger.info(
        "Generated mock note content",
        post_uid=post.post_uid,
        full_body_length=len(full_body),
        concise_body_length=len(concise_body),
        has_url=note_url in concise_body,
        generator_version=generator_version
    )
    
    return {
        "full_body": full_body,
        "concise_body": concise_body,
        "citations": citations
    }


def _call_real_langgraph_agent(
    post: Post,
    topic: Optional[Topic],
    generator_version: str
) -> Dict[str, Any]:
    """
    Real LangGraph agent implementation - replace this stub with actual LangGraph code
    
    This function should contain your actual LangGraph workflow/agent logic.
    For now, it falls back to the mock implementation.
    """
    
    # TODO: Replace this with your actual LangGraph implementation
    # Example structure:
    # from your_langgraph_module import FactCheckAgent
    # agent = FactCheckAgent()
    # result = agent.run(post.text, topic.slug if topic else None)
    # return result
    
    # For now, use the mock implementation
    return _create_mock_note_content(post, topic, generator_version)


async def get_generation_stats(session: AsyncSession) -> Dict[str, Any]:
    """Get note generation statistics"""
    from sqlalchemy import func
    
    # Count total drafts
    total_result = await session.execute(
        select(func.count(DraftNote.draft_id))
    )
    total_drafts = total_result.scalar()
    
    # Count by status
    status_result = await session.execute(
        select(DraftNote.draft_status, func.count(DraftNote.draft_id))
        .group_by(DraftNote.draft_status)
    )
    by_status = dict(status_result.fetchall())
    
    # Count by generator version
    version_result = await session.execute(
        select(DraftNote.generator_version, func.count(DraftNote.draft_id))
        .group_by(DraftNote.generator_version)
    )
    by_version = dict(version_result.fetchall())
    
    # Count regenerations
    regeneration_result = await session.execute(
        select(func.count(DraftNote.draft_id))
        .where(DraftNote.regenerated_from.is_not(None))
    )
    regenerated_count = regeneration_result.scalar()
    
    return {
        "total_drafts": total_drafts,
        "by_status": by_status,
        "by_version": by_version,
        "regenerated_count": regenerated_count,
        "current_version": GENERATOR_VERSION
    }