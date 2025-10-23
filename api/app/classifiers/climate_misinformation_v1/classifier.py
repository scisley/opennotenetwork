"""Climate Misinformation Detector v1"""

from typing import Dict, Any, Optional
import random
from app.classifiers.base import BaseClassifier
from app.classifiers.registry import register_classifier


@register_classifier
class ClimateMisinformationV1(BaseClassifier):
    slug = "climate-misinformation-v1"
    """
    Detects climate change misinformation in posts
    
    This is currently a stub implementation that returns mock data.
    Will be replaced with LangGraph agent integration.
    """
    
    async def classify(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a post for climate misinformation
        
        Args:
            post_data: Dict containing post information
            
        Returns:
            Classification result with type, value, and confidence
        """
        post_text = post_data.get("text", "")
        self.logger.info("Classifying post for climate misinformation", text_length=len(post_text))
        
        # TODO: Replace stub with LangGraph agent integration
        # from app.agents.climate_classifier import classify_climate_post
        # result = await classify_climate_post(post_data, self.config)
        # return self._parse_agent_response(result)
        
        # STUB IMPLEMENTATION - Simple keyword matching for testing
        text_lower = post_text.lower()
        
        # Get valid choices from schema
        valid_choices = [choice['value'] for choice in self.output_schema.get('choices', [])]
        
        # Simple keyword-based mock classification
        if any(word in text_lower for word in ['hoax', 'conspiracy', 'fake climate']):
            value = "climate_misinformation" if "climate_misinformation" in valid_choices else valid_choices[0]
            confidence = 0.85 + random.uniform(-0.1, 0.1)
        elif any(word in text_lower for word in ['climate change', 'global warming', 'carbon']):
            if any(word in text_lower for word in ['crisis', 'emergency', 'science']):
                value = "climate_accurate" if "climate_accurate" in valid_choices else valid_choices[0]
                confidence = 0.75 + random.uniform(-0.1, 0.1)
            else:
                value = "climate_neutral" if "climate_neutral" in valid_choices else valid_choices[0]
                confidence = 0.65 + random.uniform(-0.1, 0.1)
        else:
            value = "not_climate_related" if "not_climate_related" in valid_choices else valid_choices[-1]
            confidence = 0.90 + random.uniform(-0.05, 0.05)
        
        result = {
            "type": "single",
            "value": value,
            "confidence": round(min(max(confidence, 0.0), 1.0), 3)
        }
        
        # Validate before returning
        if not await self.validate_output(result):
            raise ValueError("Invalid classification output")
        
        self.logger.info("Classification complete", result=result)
        return result