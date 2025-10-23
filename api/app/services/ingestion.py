"""
Ingestion service for fetching Community Note requests from X.com
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.models import Post
from app.database import build_post_uid
from app.services.classification import classify_post
from app.services.x_api_client import get_x_api_client

logger = structlog.get_logger()


def _extract_tweet_dependencies(
    root_tweet: Dict[str, Any],
    includes: Dict[str, Any], 
    users_lookup: Dict[str, Any],
    media_lookup: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extract only the includes that are directly relevant to a specific tweet.
    Only includes data from directly referenced tweets (replies, quotes),
    not from other posts in the batch.
    """
    relevant_includes = {}
    processed_tweet_ids = set()
    processed_user_ids = set()
    processed_media_keys = set()
    
    def _process_tweet_recursive(tweet_data: Dict[str, Any], depth: int = 0):
        """Process a tweet and its direct dependencies only"""
        tweet_id = tweet_data.get("id")
        if tweet_id in processed_tweet_ids:
            return
        processed_tweet_ids.add(tweet_id)
        
        # Add this tweet to includes.tweets (if it's not the root tweet)
        if tweet_data != root_tweet:
            if "tweets" not in relevant_includes:
                relevant_includes["tweets"] = []
            relevant_includes["tweets"].append(tweet_data)
        
        # Process tweet author
        author_id = tweet_data.get("author_id")
        if author_id and author_id not in processed_user_ids and author_id in users_lookup:
            processed_user_ids.add(author_id)
            if "users" not in relevant_includes:
                relevant_includes["users"] = []
            relevant_includes["users"].append(users_lookup[author_id])
        
        # Process media attachments for this tweet only
        if "attachments" in tweet_data and "media_keys" in tweet_data["attachments"]:
            for media_key in tweet_data["attachments"]["media_keys"]:
                if media_key not in processed_media_keys and media_key in media_lookup:
                    processed_media_keys.add(media_key)
                    if "media" not in relevant_includes:
                        relevant_includes["media"] = []
                    relevant_includes["media"].append(media_lookup[media_key])
        
        # Only process DIRECTLY referenced tweets from the root tweet
        # Don't recursively follow references beyond the immediate references 
        # to avoid pulling in unrelated conversation context
        if depth == 0:
            referenced_tweets = tweet_data.get("referenced_tweets", [])
            # Only proceed if this tweet actually has referenced tweets
            if referenced_tweets and "tweets" in includes:
                # Create lookup for all available tweets
                tweets_lookup = {t["id"]: t for t in includes["tweets"]}
                
                for ref in referenced_tweets:
                    ref_tweet_id = ref.get("id")
                    # Only process if this reference exists in our includes
                    if ref_tweet_id and ref_tweet_id in tweets_lookup:
                        # Process the referenced tweet but don't go deeper
                        _process_tweet_recursive(tweets_lookup[ref_tweet_id], depth + 1)
    
    # Start processing from root tweet with depth 0
    _process_tweet_recursive(root_tweet, 0)
    
    return relevant_includes


@retry(
    stop=stop_after_attempt(1),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def get_posts_eligible_for_notes(
    max_results: int = 100,
    pagination_token: str = None
) -> Dict[str, Any]:
    """Fetch posts eligible for Community Notes using OAuth1"""

    try:
        logger.info("Fetching posts eligible for notes", max_results=max_results)

        # Build parameters dict for the API request
        params = {
            "test_mode": "false",
            "max_results": max_results,
            "tweet.fields": "author_id,created_at,referenced_tweets,entities,attachments,media_metadata,note_tweet,public_metrics",
            "expansions": "attachments.media_keys,referenced_tweets.id,referenced_tweets.id.attachments.media_keys,author_id,referenced_tweets.id.author_id",
            "user.fields": "description,username,name,public_metrics",
            "media.fields": "alt_text,duration_ms,height,media_key,preview_image_url,public_metrics,type,url,width,variants"
        }

        if pagination_token:
            params["pagination_token"] = pagination_token

        # Get the shared X API client
        client = get_x_api_client()

        # Make the request using OAuth1
        response = client.get(
            "/2/notes/search/posts_eligible_for_notes",
            params=params,
            timeout=30
        )

        if not response.ok:
            error_msg = f"X.com API request failed: {response.text}"
            logger.error(
                "Failed to fetch posts from X API",
                status_code=response.status_code,
                response=response.text[:500]
            )
            raise Exception(error_msg)

        data = response.json()
        logger.info(
            "Successfully fetched posts",
            count=len(data.get("data", [])),
            has_next=bool(data.get("meta", {}).get("next_token"))
        )

        return data

    except Exception as e:
        logger.error("Failed to fetch posts from X API", error=str(e))
        raise


async def run_ingestion(
    session: AsyncSession, 
    batch_size: int = 50,
    max_total_posts: int = 500,
    duplicate_threshold: float = 0.8,
    auto_classify: bool = True,
    classifier_slugs: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Run the ingestion process to fetch recent posts eligible for Community Notes

    Args:
        batch_size: Number of posts to fetch per API request (max 100)
        max_total_posts: Maximum total posts to process before stopping
        duplicate_threshold: Stop if this fraction of a batch are duplicates
        auto_classify: Whether to automatically classify new posts
        classifier_slugs: Optional list of specific classifiers to run (None = all active)
    """
    total_new = 0
    total_updated = 0
    total_classified = 0
    total_fact_checks_triggered = 0
    classification_errors = []
    errors = []
    pagination_token = None

    try:
        while (total_new + total_updated) < max_total_posts:
            # Fetch a batch of posts
            try:
                data = await get_posts_eligible_for_notes(
                    max_results=batch_size,
                    pagination_token=pagination_token
                )
            except Exception as e:
                # If pagination fails, log the error but continue with what we have
                if pagination_token:
                    logger.error(
                        "Failed to fetch with pagination token, stopping",
                        error=str(e),
                        pagination_token=pagination_token[:50] + "..." if len(pagination_token) > 50 else pagination_token
                    )
                    break
                else:
                    # If first request fails, re-raise
                    raise
            
            if not data.get("data"):
                logger.info("No more posts available")
                break
            
            # Process posts in this batch
            batch_new, batch_updated, batch_errors, new_post_uids = await _process_posts_batch(
                session, data
            )
            
            # Commit after each batch to avoid long-running transactions
            await session.commit()
            
            # Classify new posts if auto_classify is enabled
            batch_classified = 0
            batch_fact_checks_triggered = 0
            if auto_classify and new_post_uids:
                logger.info(f"Starting parallel classification for {len(new_post_uids)} new posts")
                
                # Use batch classification for parallel processing
                from app.services.classification import classify_posts_batch
                
                try:
                    batch_result = await classify_posts_batch(
                        post_uids=new_post_uids,
                        classifier_slugs=classifier_slugs,
                        max_concurrent=10,  # Limit concurrent classifications
                        trigger_fact_checks=True
                    )
                    
                    batch_classified = batch_result.get("total_classified", 0)
                    
                    # Note: fact_checks_triggered info is not returned by classify_posts_batch
                    # This would need to be added if we want to track it
                    
                    # Collect any classification errors
                    if batch_result.get("errors"):
                        for error in batch_result.get("errors", []):
                            if isinstance(error, dict):
                                classification_errors.append(error)
                            else:
                                classification_errors.append({
                                    "error": str(error)
                                })
                    
                except Exception as e:
                    logger.error(
                        "Failed to classify batch",
                        batch_size=len(new_post_uids),
                        error=str(e)
                    )
                    classification_errors.append({
                        "batch": new_post_uids,
                        "error": str(e)
                    })
            
            total_new += batch_new
            total_updated += batch_updated
            total_classified += batch_classified
            total_fact_checks_triggered += batch_fact_checks_triggered
            errors.extend(batch_errors)
            
            batch_total = batch_new + batch_updated
            total_processed = total_new + total_updated
            
            logger.info(
                "Processed batch",
                batch_new=batch_new,
                batch_updated=batch_updated,
                batch_classified=batch_classified,
                batch_fact_checks_triggered=batch_fact_checks_triggered,
                batch_total=batch_total,
                total_processed=total_processed
            )
            
            # Stop if we hit mostly duplicates (indicates we've caught up)
            if (batch_total > 0 and 
                total_processed >= batch_size and 
                (batch_updated / batch_total) >= duplicate_threshold):
                logger.info(
                    "High duplicate ratio detected, stopping ingestion",
                    duplicate_ratio=batch_updated / batch_total,
                    threshold=duplicate_threshold
                )
                break
            
            # Check for next page
            pagination_token = data.get("meta", {}).get("next_token")
            if not pagination_token:
                logger.info("No more pages available")
                break
            
            # Add a small delay between API requests to be respectful
            # X API has 90 requests per 15 minutes limit
            await asyncio.sleep(1)
        
        # Final commit for any remaining changes
        await session.commit()
        
        logger.info(
            "Ingestion completed",
            new=total_new,
            updated=total_updated,
            classified=total_classified,
            fact_checks_triggered=total_fact_checks_triggered,
            total_processed=total_new + total_updated,
            errors=len(errors),
            classification_errors=len(classification_errors)
        )
        
        return {
            "added": total_new,
            "skipped": total_updated,  # "skipped" now means "updated existing"
            "classified": total_classified,
            "fact_checks_triggered": total_fact_checks_triggered,
            "total_processed": total_new + total_updated,
            "errors": errors,
            "classification_errors": classification_errors
        }
        
    except Exception as e:
        # Ensure session is properly rolled back
        try:
            await session.rollback()
        except:
            pass  # Session might already be closed
        error_msg = f"Ingestion failed: {str(e)}"
        logger.error("Ingestion failed", error=error_msg)
        raise Exception(error_msg)


async def _process_posts_batch(
    session: AsyncSession, 
    api_response: Dict[str, Any]
) -> tuple[int, int, List[str], List[str]]:
    """Process a batch of posts from X API with expanded data"""
    new_posts = 0
    updated_posts = 0
    errors = []
    new_post_uids = []
    
    # Get the main posts data
    posts_data = api_response.get("data", [])
    
    # Create lookup tables for expanded data
    users_lookup = {}
    if "includes" in api_response and "users" in api_response["includes"]:
        for user in api_response["includes"]["users"]:
            users_lookup[user["id"]] = user
    
    media_lookup = {}
    if "includes" in api_response and "media" in api_response["includes"]:
        for media in api_response["includes"]["media"]:
            media_lookup[media["media_key"]] = media
    
    for post_data in posts_data:
        try:
            post_id = post_data["id"]
            post_uid = build_post_uid("x", post_id)
            
            # Parse created_at if available
            created_at = None
            if "created_at" in post_data:
                created_at = datetime.fromisoformat(
                    post_data["created_at"].replace("Z", "+00:00")
                )
            
            # Get author information from expanded user data
            author_handle = None
            author_id = post_data.get("author_id")
            if author_id and author_id in users_lookup:
                user_data = users_lookup[author_id]
                author_handle = user_data.get("username")  # This is the @username
            
            # Extract post text - handle note_tweet for posts > 280 chars
            post_text = post_data.get("text", "")
            
            # If post has note_tweet, use that as it contains the full text
            if "note_tweet" in post_data and "text" in post_data["note_tweet"]:
                post_text = post_data["note_tweet"]["text"]
            elif not post_text:
                # Some posts might not have direct text (e.g., retweets, media-only posts)
                post_text = f"[Post {post_id} - content may be in referenced tweets or media]"
            
            # Create cleaned enriched raw_json with recursive dependency resolution
            relevant_includes = _extract_tweet_dependencies(
                post_data, 
                api_response.get("includes", {}),
                users_lookup,
                media_lookup
            )
            
            enriched_raw_json = {
                "post": post_data,
                "includes": relevant_includes,
                "ingestion_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Create post record
            post = Post(
                post_uid=post_uid,
                platform="x",
                platform_post_id=post_id,
                author_handle=author_handle,
                text=post_text,
                raw_json=enriched_raw_json,
                created_at=created_at,
                ingested_at=datetime.now(timezone.utc)
            )
            
            # Use upsert to handle duplicates
            stmt = insert(Post).values(
                post_uid=post.post_uid,
                platform=post.platform,
                platform_post_id=post.platform_post_id,
                author_handle=post.author_handle,
                text=post.text,
                raw_json=post.raw_json,
                created_at=post.created_at,
                ingested_at=post.ingested_at
            )
            
            # Check if this post already exists (simple check for stopping logic)
            existing_check = await session.execute(
                select(Post.post_uid).where(Post.post_uid == post_uid)
            )
            is_existing = existing_check.scalar_one_or_none() is not None
            
            # On conflict, update raw_json and author_handle but keep original ingested_at
            stmt = stmt.on_conflict_do_update(
                index_elements=['post_uid'],
                set_={
                    'raw_json': stmt.excluded.raw_json,  # Update with latest expanded data
                    'author_handle': stmt.excluded.author_handle  # Update in case username changed
                }
            )
            
            await session.execute(stmt)
            
            # Track new vs updated for stopping logic
            if is_existing:
                updated_posts += 1
                logger.debug("Updated existing post", post_uid=post_uid)
            else:
                new_posts += 1
                new_post_uids.append(post_uid)
                logger.debug(
                    "Added new post", 
                    post_uid=post_uid, 
                    author=author_handle, 
                    text_length=len(post_text)
                )
                
        except Exception as e:
            post_id = post_data.get("id", "unknown")
            error_msg = f"Failed to process post {post_id}: {str(e)}"
            logger.error("Failed to process post", error=error_msg, post_data=post_data)
            errors.append(error_msg)
    
    return new_posts, updated_posts, errors, new_post_uids


async def get_ingestion_stats(session: AsyncSession) -> Dict[str, Any]:
    """Get ingestion statistics"""
    from sqlalchemy import func, select
    
    # Count total posts
    total_result = await session.execute(
        select(func.count(Post.post_uid))
    )
    total_posts = total_result.scalar()
    
    # Count posts by platform
    platform_result = await session.execute(
        select(Post.platform, func.count(Post.post_uid))
        .group_by(Post.platform)
    )
    by_platform = dict(platform_result.fetchall())
    
    # Count posts ingested in last 24 hours
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_result = await session.execute(
        select(func.count(Post.post_uid))
        .where(Post.ingested_at >= since)
    )
    recent_posts = recent_result.scalar()
    
    return {
        "total_posts": total_posts,
        "by_platform": by_platform,
        "ingested_last_24h": recent_posts
    }