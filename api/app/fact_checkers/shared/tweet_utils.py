import re

def get_original_tweet_content(post):
    """
    Extract original content from a post, handling retweets and quote tweets.
    
    Args:
        post: Dictionary with Twitter post data
        
    Returns:
        Dictionary with text, context, author, and media
    """
    
    # First check if there's a top-level 'text' field (full text)
    # This takes priority over raw_json.post.text which might be truncated
    full_text = post.get('text')
    
    def get_author_info(author_id, includes):
        """Extract author info from includes.users based on author_id"""
        users = includes.get('users', [])
        for user in users:
            if user.get('id') == author_id:
                return {
                    'name': user.get('name'),
                    'username': user.get('username'),
                    'description': user.get('description')
                }
        return None
    
    def format_author(author_info):
        """Format author info into a readable string"""
        if not author_info:
            return ""
        
        author_str = author_info.get('name', '')
        if author_info.get('username'):
            author_str += f" (@{author_info['username']})"
        if author_info.get('description'):
            author_str += f": {author_info['description']}"
        return author_str
    
    def extract_media(media_items):
        """Extract media URLs from media items and wrap in objects"""
        media_list = []
        for m in media_items:
            url = m.get('url') or m.get('preview_image_url')
            if url:
                media_obj = {'url': url}
                if m.get('type'):
                    media_obj['type'] = m.get('type')
                media_list.append(media_obj)
        return media_list
    
    def build_context(created_at, is_retweet=False, is_quote=False, original_text=None, quote_text=None, user_comment=None):
        """Build context string with tweet type and timestamp"""
        context_parts = []
        
        if is_retweet:
            context_parts.append(f'This community note is about a post that was retweeted. The original tweet content is: "{original_text}"')
        elif is_quote:
            context_parts.append(f'This community note is about a quoted tweet. The user\'s comment is: "{user_comment}" and they are quoting: "{quote_text}"')
        
        timestamp_context = f"X.com post created at {created_at}" if created_at else "X.com post"
        context_parts.append(timestamp_context)
        
        return " | ".join(context_parts) if len(context_parts) > 1 else context_parts[0] if context_parts else ""
    
    # Extract the actual post data and includes based on the structure
    if 'raw_json' in post:
        post_data = post['raw_json'].get('post', {})
        includes = post['raw_json'].get('includes', {})
    else:
        post_data = post
        includes = post.get('includes', {})
    
    # Check for referenced tweets
    referenced_tweets = post_data.get('referenced_tweets', [])
    retweet_ref = next((rt for rt in referenced_tweets if rt['type'] == 'retweeted'), None)
    quoted_ref = next((rt for rt in referenced_tweets if rt['type'] == 'quoted'), None)
    
    # Handle retweet
    if retweet_ref and post_data.get('referenced_tweet_data'):
        ref_data = post_data['referenced_tweet_data']
        author_info = get_author_info(ref_data.get('author_id'), includes)
        
        # Use full_text if available, otherwise fall back to ref_data text
        text_to_use = full_text if full_text else ref_data['text']
        
        # Media is always in includes.media for Twitter API
        media_items = includes.get('media', [])
        
        return {
            'text': text_to_use,
            'context': build_context(
                ref_data.get('created_at'),
                is_retweet=True,
                original_text=text_to_use
            ),
            'author': format_author(author_info),
            'media': extract_media(media_items)
        }
    
    # Handle quote tweet
    if quoted_ref and post_data.get('referenced_tweet_data'):
        ref_data = post_data['referenced_tweet_data']
        # Use full_text for the main text if available
        main_text = full_text if full_text else post_data["text"]
        combined_text = f'{main_text}\n\nQuoted tweet: "{ref_data["text"]}"'
        author_info = get_author_info(post_data.get('author_id'), includes)
        
        # Media is always in includes.media for Twitter API
        media_items = includes.get('media', [])
        
        return {
            'text': combined_text,
            'context': build_context(
                post_data.get('created_at'),
                is_quote=True,
                user_comment=main_text,
                quote_text=ref_data["text"]
            ),
            'author': format_author(author_info),
            'media': extract_media(media_items)
        }
    
    # Handle traditional RT format (RT @username: ...)
    # Check both full_text and post_data.text for RT pattern
    text_to_check = full_text if full_text else post_data.get('text', '')
    if text_to_check.startswith('RT @'):
        rt_match = re.match(r'^RT @(\w+): (.+)$', text_to_check, re.DOTALL)
        if rt_match:
            retweeted_username = rt_match.group(1)
            original_text = rt_match.group(2)
            
            # Try to find author by username
            author_info = None
            for user in includes.get('users', []):
                if user.get('username') == retweeted_username:
                    author_info = {
                        'name': user.get('name'),
                        'username': user.get('username'),
                        'description': user.get('description')
                    }
                    break
            
            # Media is always in includes.media for Twitter API
            media_items = includes.get('media', [])
            
            return {
                'text': original_text,
                'context': build_context(
                    post_data.get('created_at'),
                    is_retweet=True,
                    original_text=original_text
                ),
                'author': format_author(author_info),
                'media': extract_media(media_items)
            }
    
    # Regular tweet (not a retweet or quote)
    author_info = get_author_info(post_data.get('author_id'), includes)
    
    # Media is always in includes.media for Twitter API
    media_items = includes.get('media', [])
    
    # Use full_text if available, otherwise fall back to post_data.text
    text_to_use = full_text if full_text else post_data.get('text', '')
    
    return {
        'text': text_to_use,
        'context': build_context(post_data.get('created_at')),
        'author': format_author(author_info),
        'media': extract_media(media_items)
    }