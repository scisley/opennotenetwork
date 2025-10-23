"""
Media Type Classifier V1

Classifies posts based on the presence and type of media attachments.
Uses the shared tweet utilities to extract media information from raw JSON.
"""

from typing import Dict, Any, Optional, List
from app.classifiers.base import BaseClassifier
from app.classifiers.registry import register_classifier
from app.classifiers.shared.tweet_utils import extract_media_from_post


@register_classifier
class MediaTypeV1(BaseClassifier):
    slug = "media-type-v1"
    """
    Media Type Classifier

    Detects the presence and type of media in posts:
    - has_image: Post contains at least one image
    - has_multiple_images: Post contains multiple images
    - has_video: Post contains video or animated GIF
    - no_media: Post contains no media attachments
    """
    
    async def classify(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a post based on its media content
        
        Args:
            post_data: Dict containing post information including raw_json
            
        Returns:
            Multi-type classification with applicable media types
        """
        self.logger.info("Classifying post media types")
        
        # Validate required data
        if 'raw_json' not in post_data:
            raise ValueError("raw_json is required in post_data for media type classification")
        
        # Validate platform - only X/Twitter is supported
        platform = post_data.get('platform')
        if platform != 'x':
            raise ValueError(f"Media type classifier only supports platform 'x', got '{platform}'")
        
        # Extract media from raw JSON
        raw_json = post_data['raw_json']
        media_info = extract_media_from_post(raw_json)
        
        # Initialize result values
        values = []
        
        # Count images and videos
        image_count = len(media_info.get('images', []))
        video_count = len(media_info.get('videos', []))
        
        # Classify based on media presence
        if image_count > 0:
            values.append({
                "value": "has_image",
                "confidence": 1.0
            })
            
            if image_count > 1:
                values.append({
                    "value": "has_multiple_images", 
                    "confidence": 1.0
                })
        
        if video_count > 0:
            values.append({
                "value": "has_video",
                "confidence": 1.0
            })

        # If no media at all, classify as no_media
        if image_count == 0 and video_count == 0:
            values.append({
                "value": "no_media",
                "confidence": 1.0
            })

        self.logger.info(
            "Media classification complete",
            image_count=image_count,
            video_count=video_count,
            classifications=len(values)
        )
        
        return {
            "type": "multi",
            "values": values
        }