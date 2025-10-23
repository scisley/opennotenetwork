"""Topic Tagger v1"""

from typing import Dict, Any, Optional, List
import random
from app.classifiers.base import BaseClassifier
from app.classifiers.registry import register_classifier


@register_classifier
class TopicTaggerV1(BaseClassifier):
    slug = "topic-tagger-v1"
    """
    Tags posts with multiple relevant topics
    
    This is currently a stub implementation that returns mock data.
    Will be replaced with LangGraph agent integration.
    """
    
    async def classify(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tag a post with multiple topics
        
        Args:
            post_data: Dict containing post information
            
        Returns:
            Classification result with type and values array
        """
        post_text = post_data.get("text", "")
        self.logger.info("Tagging post with topics", text_length=len(post_text))
        
        # TODO: Replace stub with LangGraph agent integration
        # from app.agents.topic_tagger import tag_post_topics
        # result = await tag_post_topics(post_text, post_metadata, self.config)
        # return self._parse_agent_response(result)
        
        # STUB IMPLEMENTATION - Simple keyword matching for testing
        text_lower = post_text.lower()
        
        # Get valid choices from schema
        valid_choices = [choice['value'] for choice in self.output_schema.get('choices', [])]
        max_selections = self.output_schema.get('max_selections', 5)
        
        values = []
        
        # Simple keyword-based mock tagging (only use valid choices)
        if 'climate' in valid_choices and any(word in text_lower for word in ['climate', 'warming', 'carbon', 'temperature']):
            values.append({
                "value": "climate",
                "confidence": 0.8 + random.uniform(-0.1, 0.1)
            })
        
        if 'scientific' in valid_choices and any(word in text_lower for word in ['science', 'research', 'study', 'data']):
            values.append({
                "value": "scientific",
                "confidence": 0.7 + random.uniform(-0.1, 0.1)
            })
        
        if 'political' in valid_choices and any(word in text_lower for word in ['government', 'policy', 'election', 'congress']):
            values.append({
                "value": "political",
                "confidence": 0.75 + random.uniform(-0.1, 0.1)
            })
        
        if 'misleading' in valid_choices and any(word in text_lower for word in ['false', 'fake', 'hoax', 'conspiracy']):
            values.append({
                "value": "misleading",
                "confidence": 0.85 + random.uniform(-0.1, 0.1)
            })
        
        if 'satire' in valid_choices and any(word in text_lower for word in ['joke', 'satire', 'onion', 'parody']):
            values.append({
                "value": "satire",
                "confidence": 0.9 + random.uniform(-0.05, 0.05)
            })
        
        # If no tags found, add a random one with low confidence
        if not values and valid_choices:
            values.append({
                "value": random.choice(valid_choices),
                "confidence": 0.3 + random.uniform(-0.1, 0.1)
            })
        
        # Limit to max selections and normalize confidences
        values = values[:max_selections]
        for v in values:
            v["confidence"] = round(min(max(v["confidence"], 0.0), 1.0), 3)
        
        result = {
            "type": "multi",
            "values": values
        }
        
        # Validate before returning
        if not await self.validate_output(result):
            raise ValueError("Invalid classification output")
        
        self.logger.info("Tagging complete", num_tags=len(values))
        return result