"""
Classification service for identifying climate-related posts
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Dict, List, Any, Optional
import re
import uuid

from app.models import Post, Topic, PostTopic
from app.schemas.admin import TopicLabel

logger = structlog.get_logger()

# Current classifier version - increment when logic changes
CLASSIFIER_VERSION = "stub-v1.0"

# Climate-related keywords for basic classification
CLIMATE_KEYWORDS = [
    "climate change", "global warming", "greenhouse gas", "carbon dioxide", "co2",
    "fossil fuels", "renewable energy", "solar power", "wind energy", 
    "carbon emissions", "sea level rise", "melting ice", "polar ice caps",
    "carbon footprint", "sustainability", "clean energy", "green energy",
    "paris agreement", "cop27", "cop28", "ipcc", "carbon neutral",
    "net zero", "decarbonization", "climate crisis", "climate emergency",
    "extreme weather", "heat wave", "drought", "flooding", "hurricane",
    "wildfire", "deforestation", "ocean acidification", "arctic ice"
]

# More specific climate science terms
CLIMATE_SCIENCE_KEYWORDS = [
    "temperature anomaly", "radiative forcing", "albedo effect",
    "carbon cycle", "methane emissions", "permafrost", "tipping point",
    "climate feedback", "anthropogenic", "climatology", "paleoclimate"
]


async def run(
    post_uid: str, 
    session: AsyncSession, 
    version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run classification on a post to identify topics
    
    Args:
        post_uid: The post to classify
        session: Database session
        version: Optional classifier version to use
        
    Returns:
        Dict with topics list and classifier version
    """
    try:
        # Get the post
        result = await session.execute(
            select(Post).where(Post.post_uid == post_uid)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            raise ValueError(f"Post not found: {post_uid}")
        
        # Use specified version or default
        classifier_version = version or CLASSIFIER_VERSION
        
        # Run classification
        topics = await _classify_post(post, session, classifier_version)
        
        # Clear existing classifications for this post
        await session.execute(
            delete(PostTopic)
            .where(PostTopic.post_uid == post_uid)
            .where(PostTopic.labeled_by == "classifier")
        )
        
        # Insert new classifications
        for topic_label in topics:
            # Get topic by slug
            topic_result = await session.execute(
                select(Topic).where(Topic.slug == topic_label.topic_slug)
            )
            topic = topic_result.scalar_one_or_none()
            
            if topic:
                post_topic = PostTopic(
                    post_uid=post_uid,
                    topic_id=topic.topic_id,
                    labeled_by="classifier",
                    confidence=topic_label.confidence,
                    classifier_version=classifier_version
                )
                session.add(post_topic)
        
        # Update post classification timestamp
        from sqlalchemy import update
        from sqlalchemy.sql import func
        await session.execute(
            update(Post)
            .where(Post.post_uid == post_uid)
            .values(classified_at=func.now())
        )
        
        await session.commit()
        
        logger.info(
            "Post classified successfully",
            post_uid=post_uid,
            topics_found=len(topics),
            classifier_version=classifier_version
        )
        
        return {
            "topics": topics,
            "classifier_version": classifier_version
        }
        
    except Exception as e:
        await session.rollback()
        logger.error("Classification failed", post_uid=post_uid, error=str(e))
        raise


async def _classify_post(
    post: Post, 
    session: AsyncSession, 
    classifier_version: str
) -> List[TopicLabel]:
    """
    Classify a single post (stub implementation)
    
    This is a simple keyword-based classifier for demonstration.
    In production, this would call an ML model or external service.
    """
    text = post.text.lower()
    topics = []
    
    # Check for climate-related content
    climate_score = _calculate_climate_score(text)
    
    if climate_score > 0:
        # Determine confidence based on score
        if climate_score >= 3:
            confidence = 0.95
        elif climate_score >= 2:
            confidence = 0.80
        else:
            confidence = 0.65
        
        topics.append(TopicLabel(
            topic_slug="climate",
            confidence=confidence,
            labeled_by="classifier"
        ))
        
        logger.debug(
            "Climate classification",
            post_uid=post.post_uid,
            score=climate_score,
            confidence=confidence,
            text_preview=text[:100] + "..." if len(text) > 100 else text
        )
    
    # Could add more topic classifications here
    # e.g., politics, economics, health, etc.
    
    return topics


def _calculate_climate_score(text: str) -> int:
    """
    Calculate a climate relevance score based on keyword matching
    
    Returns:
        Integer score (higher = more climate-related)
    """
    score = 0
    
    # Check for basic climate keywords
    for keyword in CLIMATE_KEYWORDS:
        if keyword in text:
            score += 1
    
    # Bonus points for scientific climate terms
    for keyword in CLIMATE_SCIENCE_KEYWORDS:
        if keyword in text:
            score += 2
    
    # Look for climate denial patterns (still climate-related)
    denial_patterns = [
        r"climate.*hoax",
        r"global.*warming.*fake",
        r"climate.*scam",
        r"co2.*not.*cause",
        r"natural.*climate.*variation"
    ]
    
    for pattern in denial_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            score += 1
    
    # Look for climate action/policy terms
    policy_keywords = [
        "carbon tax", "emissions trading", "green new deal", 
        "climate policy", "renewable subsidies", "fossil fuel ban"
    ]
    
    for keyword in policy_keywords:
        if keyword in text:
            score += 1
    
    return min(score, 10)  # Cap at 10


async def get_classification_stats(session: AsyncSession) -> Dict[str, Any]:
    """Get classification statistics"""
    from sqlalchemy import func
    
    # Count classified posts
    classified_result = await session.execute(
        select(func.count(Post.post_uid))
        .where(Post.classified_at.is_not(None))
    )
    classified_posts = classified_result.scalar()
    
    # Count unclassified posts
    unclassified_result = await session.execute(
        select(func.count(Post.post_uid))
        .where(Post.classified_at.is_(None))
    )
    unclassified_posts = unclassified_result.scalar()
    
    # Count by topic
    topic_result = await session.execute(
        select(Topic.slug, func.count(PostTopic.post_uid))
        .join(PostTopic)
        .where(PostTopic.labeled_by == "classifier")
        .group_by(Topic.slug)
    )
    by_topic = dict(topic_result.fetchall())
    
    # Count by classifier version
    version_result = await session.execute(
        select(PostTopic.classifier_version, func.count(PostTopic.post_uid))
        .where(PostTopic.labeled_by == "classifier")
        .group_by(PostTopic.classifier_version)
    )
    by_version = dict(version_result.fetchall())
    
    return {
        "classified_posts": classified_posts,
        "unclassified_posts": unclassified_posts,
        "by_topic": by_topic,
        "by_version": by_version,
        "current_version": CLASSIFIER_VERSION
    }