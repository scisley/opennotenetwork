import re
from typing import Dict, Any, List, Literal, Optional

# ============================================================================
# CORE UTILITY FUNCTIONS - Used by all other functions
# ============================================================================

AUTHOR_CONTEXT_CONTENT_PROMPT = """# Author 
{author}

# Origin
{context}

# Content
{text}
"""

def get_author_info(author_id: str, includes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract author info from includes.users based on author_id"""
    for user in includes.get('users', []):
        if user.get('id') == author_id:
            return {
                'name': user.get('name'),
                'username': user.get('username'),
                'description': user.get('description')
            }
    return None


def format_author(author_info: Optional[Dict[str, Any]], include_description: bool = False) -> str:
    """Format author info into a readable string"""
    if not author_info:
        return "Unknown author"
    
    author_str = author_info.get('name', '')
    if author_info.get('username'):
        author_str += f" (@{author_info['username']})"
    if include_description and author_info.get('description'):
        author_str += f": {author_info['description']}"
    return author_str or "Unknown author"


def get_referenced_tweet(tweet_id: str, includes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract referenced tweet from includes.tweets based on tweet_id"""
    for tweet in includes.get('tweets', []):
        if tweet.get('id') == tweet_id:
            return tweet
    return None


def extract_media_urls(includes: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract media URLs from includes.media and wrap in objects"""
    media_list = []
    for m in includes.get('media', []):
        url = m.get('url') or m.get('preview_image_url')
        if url:
            media_obj = {'url': url}
            if m.get('type'):
                media_obj['type'] = m.get('type')
            media_list.append(media_obj)
    return media_list


def extract_raw_json_parts(post_data: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Extract post and includes from raw_json structure.
    Validates that the post has the expected structure.
    """
    if 'raw_json' not in post_data:
        raise ValueError("post_data must contain 'raw_json' field from database")
    
    raw_json = post_data['raw_json']
    post_json = raw_json.get('post', {})
    includes = raw_json.get('includes', {})
    
    return post_json, includes


def remove_quote_tweet_url(text: str, entities: Dict[str, Any], referenced_tweets: List[Dict[str, Any]]) -> str:
    """
    Remove the trailing URL that links to a quoted tweet.
    
    Twitter adds a t.co URL at the end of tweets with quotes that links to the quoted tweet.
    This URL is not shown in the Twitter UI and can confuse LLMs.
    
    Args:
        text: The tweet text
        entities: The entities object containing URL mappings
        referenced_tweets: List of referenced tweets
        
    Returns:
        Text with quote tweet URL removed
    """
    if not text or not entities or not referenced_tweets:
        return text
    
    # Check if this tweet has a quoted tweet
    has_quote = any(rt.get('type') == 'quoted' for rt in referenced_tweets)
    if not has_quote:
        return text
    
    # Find URLs that are likely quote tweet links
    urls = entities.get('urls', [])
    for url_entity in urls:
        # Quote tweet URLs don't have media_key and usually appear at the end
        if 'media_key' not in url_entity:
            expanded = url_entity.get('expanded_url', '')
            # Check if this is a Twitter/X status URL
            if 'twitter.com/' in expanded and '/status/' in expanded:
                # Remove this URL from the text
                start = url_entity.get('start', 0)
                end = url_entity.get('end', len(text))
                
                # Only remove if it's at or near the end of the text (within last 5 chars)
                if end >= len(text) - 5:
                    text = text[:start].rstrip()
                    break
    
    return text


def replace_media_urls_with_placeholders(text: str, entities: Dict[str, Any], media_list: List[Dict[str, Any]]) -> str:
    """
    Replace t.co URLs that point to media with readable placeholders.
    
    Args:
        text: The tweet text containing t.co URLs
        entities: The entities object from the tweet containing URL mappings
        media_list: List of media objects from includes.media
        
    Returns:
        Text with media URLs replaced by [[photo: url]], [[video: url]], or [[animated_gif: url]]
    """
    if not text or not entities or not media_list:
        return text
    
    # Create a mapping of media_key to media object
    media_by_key = {}
    for media in media_list:
        if 'media_key' in media:
            media_by_key[media['media_key']] = media
    
    # Process each URL in entities
    urls = entities.get('urls', [])
    modified_text = text
    
    # Group URLs by their position (start, end) since Twitter reuses the same URL for multiple media
    url_positions = {}
    for url_entity in urls:
        media_key = url_entity.get('media_key')
        if not media_key or media_key not in media_by_key:
            continue
        
        start = url_entity.get('start', 0)
        end = url_entity.get('end', len(text))
        position = (start, end)
        
        if position not in url_positions:
            url_positions[position] = []
        
        media = media_by_key[media_key]
        media_type = media.get('type', 'photo')
        
        # Get the actual media URL based on type
        if media_type == 'photo':
            actual_url = media.get('url')
        elif media_type == 'animated_gif':
            # For animated GIFs, get the video URL from variants if available
            variants = media.get('variants', [])
            if variants:
                # For GIFs, just take the first variant (usually only one)
                actual_url = variants[0].get('url')
            else:
                actual_url = media.get('url') or media.get('preview_image_url')
        elif media_type == 'video':
            # For videos, get the lowest bitrate MP4 from variants
            variants = media.get('variants', [])
            mp4_variants = [v for v in variants if v.get('content_type') == 'video/mp4']
            if mp4_variants:
                # Sort by bitrate and take the lowest
                mp4_variants.sort(key=lambda x: x.get('bit_rate', float('inf')))
                actual_url = mp4_variants[0].get('url')
            else:
                # Fallback to preview if no video URLs available
                actual_url = media.get('preview_image_url') or media.get('url')
        else:
            # Unknown media type, use what we have
            actual_url = media.get('url') or media.get('preview_image_url')
        
        if actual_url:
            url_positions[position].append(f"[[{media_type}: {actual_url}]]")
    
    # Sort positions by start in reverse to avoid position shifts during replacement
    sorted_positions = sorted(url_positions.keys(), key=lambda x: x[0], reverse=True)
    
    # Apply all replacements
    for start, end in sorted_positions:
        placeholders = url_positions[(start, end)]
        if placeholders and 0 <= start < end <= len(modified_text):
            # Join all media placeholders for this position with a space
            replacement = ' '.join(placeholders)
            modified_text = modified_text[:start] + replacement + modified_text[end:]
    
    return modified_text


# ============================================================================
# MEDIA EXTRACTION
# ============================================================================

def extract_media_from_post(raw_json: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract media information from a post's raw JSON.
    
    Note: The includes.media should already be filtered to only contain
    relevant media by prepare_fact_check_input.
    
    Args:
        raw_json: The raw JSON data from Twitter API
        
    Returns:
        Dictionary with 'images' and 'videos' lists
    """
    images = []
    videos = []
    
    includes = raw_json.get('includes', {})
    
    for media in includes.get('media', []):
        media_type = media.get('type', '')
        
        if media_type == 'photo':
            url = media.get('url')
            if url:
                images.append({'url': url, 'type': 'photo'})
        elif media_type == 'video':
            # For videos, get the lowest bitrate MP4
            video_info = {'type': media_type}
            
            # Get video URL from variants
            variants = media.get('variants', [])
            mp4_variants = [v for v in variants if v.get('content_type') == 'video/mp4']
            if mp4_variants:
                # Sort by bitrate and take the lowest
                mp4_variants.sort(key=lambda x: x.get('bit_rate', float('inf')))
                video_info['url'] = mp4_variants[0].get('url')
                video_info['bit_rate'] = mp4_variants[0].get('bit_rate')
            
            # Add thumbnail if available
            preview_url = media.get('preview_image_url')
            if preview_url:
                video_info['thumbnail'] = preview_url
            
            # Add duration if available
            if 'duration_ms' in media:
                video_info['duration_ms'] = media['duration_ms']
            
            # Only add if we have at least a URL or thumbnail
            if 'url' in video_info or 'thumbnail' in video_info:
                videos.append(video_info)
                
        elif media_type == 'animated_gif':
            # For animated GIFs, get the video URL
            gif_info = {'type': media_type}
            
            # Get GIF URL from variants
            variants = media.get('variants', [])
            if variants:
                # For GIFs, usually just one variant
                gif_info['url'] = variants[0].get('url')
            
            # Add thumbnail if available
            preview_url = media.get('preview_image_url')
            if preview_url:
                gif_info['thumbnail'] = preview_url
            
            # Only add if we have at least a URL or thumbnail
            if 'url' in gif_info or 'thumbnail' in gif_info:
                videos.append(gif_info)
    
    return {
        'images': images,
        'videos': videos
    }


# ============================================================================
# TWEET TYPE DETECTION
# ============================================================================

def get_tweet_type(raw_json: Dict[str, Any]) -> Literal["standalone", "reply", "quoted_tweet", "reply_with_quote"]:
    """
    Determine the type of tweet from raw JSON for fact-checking context.
    
    Args:
        raw_json: The raw JSON data from Twitter API
        
    Returns:
        "standalone", "reply", "quoted_tweet", or "reply_with_quote"
    """
    post_data = raw_json.get('post', {})
    referenced_tweets = post_data.get('referenced_tweets', [])
    
    if not referenced_tweets:
        return "standalone"
    
    has_reply = any(rt['type'] == 'replied_to' for rt in referenced_tweets)
    has_quote = any(rt['type'] == 'quoted' for rt in referenced_tweets)
    
    if has_reply and has_quote:
        return "reply_with_quote"
    elif has_reply:
        return "reply"
    elif has_quote:
        return "quoted_tweet"
    else:
        return "standalone"


# ============================================================================
# MEDIA FORMATTING FOR LLM CONSUMPTION
# ============================================================================

def format_content_with_media(fact_check_input: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Format text with inline media placeholders into a content array for LLM consumption.
    
    This function takes the output from prepare_fact_check_input where media URLs
    are already embedded in the text as placeholders like [[photo: url]] or [[video: url]],
    and converts them into a properly formatted content array for LLM APIs.
    
    Args:
        fact_check_input: Output from prepare_fact_check_input containing:
            - text: Text with inline media placeholders [[type: url]]
            - media: List of media objects with additional metadata
            
    Returns:
        List of content items that can be used as message["content"]
        If no media placeholders are found, returns just the text string.
    """
    text = fact_check_input.get("text", "")
    media_list = fact_check_input.get("media", [])
    
    # If no text, return empty
    if not text:
        return ""
    
    # Create a mapping of URLs to media objects for additional metadata
    media_by_url = {}
    for media in media_list:
        if "url" in media:
            media_by_url[media["url"]] = media
    
    # Pattern to match [[type: url]] placeholders
    import re
    pattern = r'\[\[([^:]+):\s*([^\]]+)\]\]'
    
    # Find all media placeholders in the text
    matches = list(re.finditer(pattern, text))
    
    # If no media placeholders found, return just the text
    if not matches:
        return text
    
    # Build content array by splitting text and inserting media
    content = []
    last_pos = 0
    
    for match in matches:
        # Add text before this media placeholder (if any)
        text_before = text[last_pos:match.start()].rstrip()
        if text_before:
            content.append({"type": "text", "text": text_before})
        
        # Extract media type and URL from placeholder
        media_type = match.group(1).strip().lower()
        media_url = match.group(2).strip()
        
        # Get additional metadata if available
        media_obj = media_by_url.get(media_url, {})
        
        # Handle different media types
        if media_type == "photo":
            # Photos are directly included as images
            content.append({
                "type": "image_url",
                "image_url": {"url": media_url}
            })
        
        elif media_type == "video":
            # For videos, check if we have a thumbnail in the media object
            thumbnail = media_obj.get("thumbnail")
            
            if thumbnail:
                # Add note about video and include thumbnail
                content.append({
                    "type": "text",
                    "text": f" [Video thumbnail - full video at: {media_url}]"
                })
                content.append({
                    "type": "image_url", 
                    "image_url": {"url": thumbnail}
                })
            else:
                # No thumbnail, keep as text reference
                content.append({
                    "type": "text",
                    "text": f" [Video: {media_url}]"
                })
        
        elif media_type == "animated_gif":
            # For GIFs, similar to videos
            thumbnail = media_obj.get("thumbnail")
            
            if thumbnail:
                content.append({
                    "type": "text",
                    "text": f" [Animated GIF thumbnail - view at: {media_url}]"
                })
                content.append({
                    "type": "image_url",
                    "image_url": {"url": thumbnail}
                })
            else:
                content.append({
                    "type": "text",
                    "text": f" [Animated GIF: {media_url}]"
                })
        
        else:
            # Unknown media type, keep as text
            content.append({
                "type": "text",
                "text": f" [{media_type}: {media_url}]"
            })
        
        # Update position after this match
        last_pos = match.end()
    
    # Add any remaining text after the last media placeholder
    remaining_text = text[last_pos:].rstrip()
    if remaining_text:
        content.append({"type": "text", "text": remaining_text})
    
    # Merge consecutive text blocks to avoid fragmentation
    merged_content = []
    for item in content:
        if item["type"] == "text" and merged_content and merged_content[-1]["type"] == "text":
            # Merge with previous text block
            merged_content[-1]["text"] += item["text"]
        else:
            merged_content.append(item)
    
    return merged_content


# ============================================================================
# MEDIA FILTERING
# ============================================================================

def _filter_relevant_media(post_json: Dict[str, Any], includes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter includes.media to only contain media relevant to this post and its directly referenced tweets.
    
    This prevents media from unrelated posts in the batch from being included.
    """
    # Collect all relevant media keys
    relevant_media_keys = set()
    
    # Add media from the main post
    if 'attachments' in post_json and 'media_keys' in post_json['attachments']:
        relevant_media_keys.update(post_json['attachments']['media_keys'])
    
    # Add media from directly referenced tweets (replies, quotes)
    referenced_tweets = post_json.get('referenced_tweets', [])
    if referenced_tweets and 'tweets' in includes:
        for ref in referenced_tweets:
            ref_id = ref.get('id')
            # Find the referenced tweet in includes
            for tweet in includes['tweets']:
                if tweet.get('id') == ref_id:
                    # Add media from this referenced tweet
                    if 'attachments' in tweet and 'media_keys' in tweet['attachments']:
                        relevant_media_keys.update(tweet['attachments']['media_keys'])
                    break
    
    # Filter the media array to only include relevant media
    if relevant_media_keys and 'media' in includes:
        filtered_media = []
        for media in includes['media']:
            if media.get('media_key') in relevant_media_keys:
                filtered_media.append(media)
        
        # Create a new includes dict with filtered media
        filtered_includes = includes.copy()
        filtered_includes['media'] = filtered_media
        return filtered_includes
    
    return includes


# ============================================================================
# MAIN FACT-CHECKING INPUT PREPARATION
# ============================================================================

def prepare_fact_check_input(post_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare standardized input for fact checkers from a post.
    
    This is the single function that all fact checkers should use to get
    properly formatted input with full context based on tweet type.
    
    Args:
        post_data: Post data from database with raw_json field
        
    Returns:
        Dictionary with:
        - text: The full text to fact-check (including quoted tweets if applicable)
        - context: Detailed context string explaining the tweet type and relationships
        - author: Primary author information
        - media: List of media attachments
        - metadata: Additional structured data for advanced fact-checkers
    """
    # Validate platform
    if post_data.get('platform') != 'x':
        raise ValueError(f"prepare_fact_check_input only supports platform 'x', got '{post_data.get('platform')}'")
    
    # Extract components using shared utilities
    post_json, includes = extract_raw_json_parts(post_data)
    
    # Filter includes.media to only contain media relevant to this post and its references
    includes = _filter_relevant_media(post_json, includes)
    
    # Get tweet type
    tweet_type = get_tweet_type(post_data['raw_json'])
    
    # Extract media using the filtered includes
    filtered_raw_json = {'post': post_json, 'includes': includes}
    media_info = extract_media_from_post(filtered_raw_json)
    all_media = media_info.get('images', []) + media_info.get('videos', [])
    
    # Get main tweet author
    main_author_id = post_json.get('author_id')
    main_author_info = get_author_info(main_author_id, includes)
    main_author_str = format_author(main_author_info)
    
    # Get the full text - the ingestion service already handles note_tweet assembly
    # The post_data['text'] field contains the complete text
    main_text = post_data.get('text', '')
    
    # If no text in post_data, fall back to raw_json
    if not main_text:
        if 'note_tweet' in post_json and post_json['note_tweet'].get('text'):
            main_text = post_json['note_tweet']['text']
        else:
            main_text = post_json.get('text', '')
    
    # Remove quote tweet URL if this is a quoted tweet
    referenced_tweets = post_json.get('referenced_tweets', [])
    main_text = remove_quote_tweet_url(
        main_text,
        post_json.get('entities', {}),
        referenced_tweets
    )
    
    # For long tweets (note_tweets), the text is clean without media URLs
    # We need to append media as placeholders at the end
    # For regular tweets, we need to replace t.co URLs with media placeholders
    if 'note_tweet' in post_json and includes.get('media'):
        # For note tweets, append media placeholders at the end
        media_placeholders = []
        for media in includes.get('media', []):
            media_type = media.get('type', 'photo')
            
            # Get the actual media URL based on type
            if media_type == 'photo':
                actual_url = media.get('url')
            elif media_type == 'animated_gif':
                variants = media.get('variants', [])
                actual_url = variants[0].get('url') if variants else (media.get('url') or media.get('preview_image_url'))
            elif media_type == 'video':
                variants = media.get('variants', [])
                mp4_variants = [v for v in variants if v.get('content_type') == 'video/mp4']
                if mp4_variants:
                    mp4_variants.sort(key=lambda x: x.get('bit_rate', float('inf')))
                    actual_url = mp4_variants[0].get('url')
                else:
                    actual_url = media.get('preview_image_url') or media.get('url')
            else:
                actual_url = media.get('url') or media.get('preview_image_url')
            
            if actual_url:
                media_placeholders.append(f"[[{media_type}: {actual_url}]]")
        
        if media_placeholders:
            main_text = main_text + "\n\n" + " ".join(media_placeholders)
    else:
        # For regular tweets, replace inline t.co URLs with placeholders
        main_text = replace_media_urls_with_placeholders(
            main_text, 
            post_json.get('entities', {}), 
            includes.get('media', [])
    )
    
    # Process URLs: replace t.co with expanded versions and collect external URLs
    entities = post_json.get('entities', {})
    url_entities = entities.get('urls', [])
    external_urls = []
    
    if url_entities:
        for url_obj in url_entities:
            short_url = url_obj.get('url', '')
            expanded_url = url_obj.get('unwound_url') or url_obj.get('expanded_url', '')
            
            if short_url and expanded_url:
                # Skip if it's a Twitter media URL or quote tweet URL
                is_media_url = any(pattern in expanded_url for pattern in ['/photo/', '/video/'])
                
                # Check if it's a quoted tweet URL
                is_quote_url = False
                if '/status/' in expanded_url:
                    for ref in referenced_tweets:
                        if ref.get('type') == 'quoted' and ref.get('id') in expanded_url:
                            is_quote_url = True
                            break
                
                # Process non-media, non-quote URLs
                if not (is_media_url or is_quote_url):
                    # Replace t.co URL with expanded URL in text
                    main_text = main_text.replace(short_url, expanded_url)
                    
                    # Add to external URLs list
                    external_urls.append({
                        "url": expanded_url,
                        "type": "link",
                        "title": url_obj.get('title'),
                        "description": url_obj.get('description')
                    })
    
    # Common metadata
    base_metadata = {
        "tweet_type": tweet_type,
        "tweet_id": post_json.get('id'),
        "created_at": post_json.get('created_at'),
        "platform": "x"
    }
    
    # Process based on tweet type
    if tweet_type == "standalone":
        created_at = post_json.get('created_at', '')
        return {
            "text": main_text,
            "context": f"X.com post from {created_at}" if created_at else "X.com post",
            "author": main_author_str,
            "media": all_media,
            "urls": external_urls,
            "metadata": base_metadata
        }
    
    elif tweet_type == "reply":
        return _prepare_reply_context(
            post_json, includes, main_text, main_author_str, 
            main_author_id, all_media, external_urls, base_metadata
        )
    
    elif tweet_type == "quoted_tweet":
        return _prepare_quote_context(
            post_json, includes, main_text, main_author_str,
            all_media, external_urls, base_metadata
        )
    
    elif tweet_type == "reply_with_quote":
        return _prepare_reply_with_quote_context(
            post_json, includes, main_text, main_author_str,
            main_author_id, all_media, external_urls, base_metadata
        )
    
    else:
        # Shouldn't happen, but handle gracefully
        return {
            "text": main_text,
            "context": f"X.com post by {main_author_str} (unknown type: {tweet_type})",
            "author": main_author_str,
            "media": all_media,
            "urls": external_urls,
            "metadata": base_metadata
        }


def _prepare_reply_context(post_json, includes, main_text, main_author_str, 
                           main_author_id, all_media, external_urls, base_metadata):
    """Helper function to prepare reply context"""
    parent_tweet = None
    parent_author_str = "Unknown"
    parent_username = None
    parent_created_at = None
    
    # Find parent tweet
    for ref in post_json.get('referenced_tweets', []):
        if ref['type'] == 'replied_to':
            parent_tweet = get_referenced_tweet(ref['id'], includes)
            if parent_tweet:
                parent_author_info = get_author_info(parent_tweet.get('author_id'), includes)
                parent_author_str = format_author(parent_author_info)
                # Extract username from formatted string
                if '(@' in parent_author_str and ')' in parent_author_str:
                    parent_username = parent_author_str.split('(@')[1].rstrip(')')
                # Get parent tweet creation date
                parent_created_at = parent_tweet.get('created_at')
            break
    
    # If we couldn't get the username from the parent tweet author, try mentions
    if not parent_username:
        # First mention in a reply is typically who you're replying to
        mentions = post_json.get('entities', {}).get('mentions', [])
        if mentions:
            parent_username = mentions[0].get('username')
            if parent_username and parent_author_str == "Unknown":
                parent_author_str = f"@{parent_username}"
    
    # Check if it's a thread (self-reply)
    is_thread = parent_tweet and parent_tweet.get('author_id') == main_author_id
    
    # Get creation date
    created_at = post_json.get('created_at', '')
    date_context = f" from {created_at}" if created_at else ""
    
    # Build context (simplified, without tweet text)
    if is_thread:
        context = f"Thread continuation{date_context} by {main_author_str}"
    else:
        # Use username if available, otherwise use formatted author string
        reply_to = f"@{parent_username}" if parent_username else parent_author_str
        context = f"Reply{date_context} by {main_author_str} to {reply_to}"
    
    # Build formatted text with clear sections
    full_text = f"### Post to be fact checked\n{main_text}\n\n"
    
    if parent_tweet and parent_tweet.get('text'):
        # Replace media URLs in parent tweet text
        parent_text = replace_media_urls_with_placeholders(
            parent_tweet['text'],
            parent_tweet.get('entities', {}),
            includes.get('media', [])
        )
        
        # Format date for parent tweet
        date_str = f" (posted {parent_created_at})" if parent_created_at else ""
        
        if is_thread:
            full_text += f"### Previous tweet in thread{date_str}\n{parent_text}"
        else:
            # Use the parent_username we already extracted
            if parent_username:
                full_text += f"### Was in reply to @{parent_username}{date_str}\n{parent_text}"
            else:
                full_text += f"### Was in reply to {parent_author_str}{date_str}\n{parent_text}"
    else:
        # Parent tweet unavailable but we might have username from mentions
        if parent_username:
            full_text += f"### Was in reply to @{parent_username}\n[Tweet unavailable]"
        else:
            full_text += f"### Was in reply to\n[Tweet unavailable]"
    
    return {
        "text": full_text,
        "context": context,
        "author": main_author_str,
        "media": all_media,
        "urls": external_urls,
        "metadata": {
            **base_metadata,
            "is_thread": is_thread,
            "parent_tweet_id": parent_tweet.get('id') if parent_tweet else None,
        }
    }


def _prepare_quote_context(post_json, includes, main_text, main_author_str,
                           all_media, external_urls, base_metadata):
    """Helper function to prepare quoted tweet context"""
    quoted_tweet = None
    quoted_author_str = "Unknown"
    
    # Find quoted tweet
    for ref in post_json.get('referenced_tweets', []):
        if ref['type'] == 'quoted':
            quoted_tweet = get_referenced_tweet(ref['id'], includes)
            if quoted_tweet:
                quoted_author_info = get_author_info(quoted_tweet.get('author_id'), includes)
                quoted_author_str = format_author(quoted_author_info)
            break
    
    # Get creation date
    created_at = post_json.get('created_at', '')
    date_context = f" from {created_at}" if created_at else ""
    
    # Build context (simplified, without tweet text)
    # Extract username if available for cleaner context
    quoted_username = None
    if '(@' in quoted_author_str and ')' in quoted_author_str:
        quoted_username = quoted_author_str.split('(@')[1].rstrip(')')
    
    quoted_ref = f"@{quoted_username}" if quoted_username else quoted_author_str
    context = f"Quote tweet{date_context} by {main_author_str} commenting on {quoted_ref}'s tweet"
    
    # Build formatted text with clear sections
    if quoted_tweet and quoted_tweet.get('text'):
        # Replace media URLs in quoted tweet text
        quoted_text = replace_media_urls_with_placeholders(
            quoted_tweet['text'],
            quoted_tweet.get('entities', {}),
            includes.get('media', [])
        )
        
        full_text = f"### Post to be fact checked\n{main_text}\n\n### Quoted tweet\n"
        # Extract username if available
        if '(@' in quoted_author_str and ')' in quoted_author_str:
            username = quoted_author_str.split('(@')[1].rstrip(')')
            full_text += f"@{username}: {quoted_text}"
        else:
            full_text += f"{quoted_author_str}: {quoted_text}"
    else:
        # Quoted tweet unavailable
        full_text = f"### Post to be fact checked\n{main_text}\n\n### Quoted tweet\n[Tweet unavailable]"
    
    return {
        "text": full_text,
        "context": context,
        "author": main_author_str,
        "media": all_media,
        "urls": external_urls,
        "metadata": {
            **base_metadata,
            "quoted_tweet_id": quoted_tweet.get('id') if quoted_tweet else None,
            "quoted_author": quoted_author_str,
            "user_comment": main_text,
            "quoted_text": quoted_tweet.get('text') if quoted_tweet else None,
        }
    }


def _prepare_reply_with_quote_context(post_json, includes, main_text, main_author_str,
                                      main_author_id, all_media, external_urls, base_metadata):
    """Helper function to prepare reply with quote context"""
    parent_tweet = None
    quoted_tweet = None
    parent_author_str = "Unknown"
    quoted_author_str = "Unknown"
    parent_username = None
    quoted_username = None
    
    # Find referenced tweets
    for ref in post_json.get('referenced_tweets', []):
        if ref['type'] == 'replied_to':
            parent_tweet = get_referenced_tweet(ref['id'], includes)
            if parent_tweet:
                parent_author_info = get_author_info(parent_tweet.get('author_id'), includes)
                parent_author_str = format_author(parent_author_info)
                # Extract username
                if '(@' in parent_author_str and ')' in parent_author_str:
                    parent_username = parent_author_str.split('(@')[1].rstrip(')')
        elif ref['type'] == 'quoted':
            quoted_tweet = get_referenced_tweet(ref['id'], includes)
            if quoted_tweet:
                quoted_author_info = get_author_info(quoted_tweet.get('author_id'), includes)
                quoted_author_str = format_author(quoted_author_info)
                # Extract username
                if '(@' in quoted_author_str and ')' in quoted_author_str:
                    quoted_username = quoted_author_str.split('(@')[1].rstrip(')')
    
    # If parent tweet not available, try to get username from mentions
    if not parent_tweet and not parent_username:
        mentions = post_json.get('entities', {}).get('mentions', [])
        if mentions:
            parent_username = mentions[0].get('username')
            if parent_username:
                parent_author_str = f"@{parent_username}"
    
    # Check if thread
    is_thread = parent_tweet and parent_tweet.get('author_id') == main_author_id
    
    # Get creation date
    created_at = post_json.get('created_at', '')
    date_context = f" from {created_at}" if created_at else ""
    
    # Build context (simplified, without tweet text)
    parent_ref = f"@{parent_username}" if parent_username else parent_author_str
    quoted_ref = f"@{quoted_username}" if quoted_username else quoted_author_str
    
    if is_thread:
        context = f"Thread continuation{date_context} by {main_author_str} that also quotes {quoted_ref}"
    else:
        context = f"Reply{date_context} by {main_author_str} to {parent_ref} that also quotes {quoted_ref}"
    
    # Build formatted text with clear sections
    full_text = f"### Post to be fact checked\n{main_text}\n\n"
    
    # Add parent tweet section
    if parent_tweet and parent_tweet.get('text'):
        # Replace media URLs in parent tweet text
        parent_text = replace_media_urls_with_placeholders(
            parent_tweet['text'],
            parent_tweet.get('entities', {}),
            includes.get('media', [])
        )
        
        if is_thread:
            full_text += f"### Previous tweet in thread\n{parent_text}\n\n"
        else:
            # Use the parent_username we already extracted
            if parent_username:
                full_text += f"### Was in reply to\n@{parent_username}: {parent_text}\n\n"
            else:
                full_text += f"### Was in reply to\n{parent_author_str}: {parent_text}\n\n"
    else:
        # Parent tweet unavailable but we might have username from mentions
        if parent_username:
            full_text += f"### Was in reply to\n@{parent_username}: [Tweet unavailable]\n\n"
        else:
            full_text += f"### Was in reply to\n[Tweet unavailable]\n\n"
    
    # Add quoted tweet section
    if quoted_tweet and quoted_tweet.get('text'):
        # Replace media URLs in quoted tweet text
        quoted_text = replace_media_urls_with_placeholders(
            quoted_tweet['text'],
            quoted_tweet.get('entities', {}),
            includes.get('media', [])
        )
        
        full_text += f"### Also quoted this tweet\n"
        # Use the quoted_username we already extracted
        if quoted_username:
            full_text += f"@{quoted_username}: {quoted_text}"
        else:
            full_text += f"{quoted_author_str}: {quoted_text}"
    else:
        full_text += f"### Also quoted this tweet\n[Tweet unavailable]"
    
    return {
        "text": full_text,
        "context": context,
        "author": main_author_str,
        "media": all_media,
        "urls": external_urls,
        "metadata": {
            **base_metadata,
            "is_thread": is_thread,
            "parent_tweet_id": parent_tweet.get('id') if parent_tweet else None,
            "quoted_tweet_id": quoted_tweet.get('id') if quoted_tweet else None,
        }
    }
