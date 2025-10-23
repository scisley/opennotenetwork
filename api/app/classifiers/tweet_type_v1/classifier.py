"""
Tweet Type Classifier V1

Classifies posts by their type for fact-checking context determination.
Uses the shared tweet utilities to analyze tweet structure from raw JSON.
"""

from typing import Dict, Any, Optional
from app.classifiers.base import BaseClassifier
from app.classifiers.registry import register_classifier
from app.classifiers.shared.tweet_utils import get_tweet_type


@register_classifier
class TweetTypeV1(BaseClassifier):
    slug = "tweet-type-v1"
    """
    Tweet Type Classifier
    
    Identifies the type of tweet for fact-checking context:
    - standalone: Original tweet with no references
    - reply: Reply to another tweet
    - quoted_tweet: Quote tweet with user commentary
    - reply_with_quote: Reply that also quotes another tweet
    """
    
    async def classify(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a post based on its tweet type
        
        Args:
            post_data: Dict containing post information including raw_json
            
        Returns:
            Single-type classification with the tweet type
        """
        self.logger.info("Classifying tweet type")
        
        # Validate required data
        if 'raw_json' not in post_data:
            raise ValueError("raw_json is required in post_data for tweet type classification")
        
        # Validate platform - only X/Twitter is supported
        platform = post_data.get('platform')
        if platform != 'x':
            raise ValueError(f"Tweet type classifier only supports platform 'x', got '{platform}'")
        
        # Determine tweet type from raw JSON
        raw_json = post_data['raw_json']
        tweet_type = get_tweet_type(raw_json)
        
        self.logger.info(
            "Tweet type classification complete",
            tweet_type=tweet_type
        )
        
        return {
            "type": "single",
            "value": tweet_type,
            "confidence": 1.0  # High confidence since we're using structural analysis
        }