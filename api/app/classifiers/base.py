"""Base classifier abstract class"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import structlog
from langsmith import tracing_context

logger = structlog.get_logger()


class BaseClassifier(ABC):
    """Abstract base class for all classifiers"""

    def __init__(self, slug: str, output_schema: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize classifier

        Args:
            slug: Unique identifier for this classifier
            output_schema: Output schema from database
            config: Optional configuration from database
        """
        self.slug = slug
        self.output_schema = output_schema
        self.config = config or {}
        self.logger = logger.bind(classifier=slug)

    @property
    def no_tracing(self):
        """Context manager to disable LangSmith tracing for classifier calls"""
        return tracing_context(enabled=False)
    
    @abstractmethod
    async def classify(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a post
        
        Args:
            post_data: Dict containing:
                - post_uid: Unique identifier
                - text: Post text  
                - platform: Platform name (e.g., 'x')
                - raw_json: Full JSON with media and metadata
                - author_handle: Author information
                - classifications: Previous classifications (optional)
            
        Returns:
            Classification data matching the output_schema format
            Should include 'type' field and appropriate data structure
        """
        pass
    
    def get_output_schema(self) -> Dict[str, Any]:
        """
        Get the output schema for this classifier
        
        Returns:
            Output schema dictionary from database
        """
        return self.output_schema
    
    async def validate_output(self, classification_data: Dict[str, Any]) -> bool:
        """
        Validate that classification data matches expected schema
        
        Args:
            classification_data: The classification result to validate
            
        Returns:
            True if valid, False otherwise
        """
        schema = self.output_schema
        
        # Check type field
        if 'type' not in classification_data:
            self.logger.error("Missing 'type' field in classification data")
            return False
        
        if classification_data['type'] != schema['type']:
            self.logger.error(
                "Type mismatch", 
                expected=schema['type'], 
                got=classification_data['type']
            )
            return False
        
        # Type-specific validation
        if schema['type'] == 'single':
            if 'value' not in classification_data:
                self.logger.error("Missing 'value' field for single-type classification")
                return False
                
        elif schema['type'] == 'multi':
            if 'values' not in classification_data or not isinstance(classification_data['values'], list):
                self.logger.error("Missing or invalid 'values' field for multi-type classification")
                return False
                
        elif schema['type'] == 'hierarchical':
            if 'levels' not in classification_data or not isinstance(classification_data['levels'], list):
                self.logger.error("Missing or invalid 'levels' field for hierarchical classification")
                return False
        
        return True