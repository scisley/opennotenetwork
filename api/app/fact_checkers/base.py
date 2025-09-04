from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class FactCheckResult(BaseModel):
    """Standard output format for all fact checkers"""
    text: str = Field(..., description="Full markdown-formatted fact check content")
    verdict: str = Field(..., description="Overall verdict: true/false/misleading/unverifiable/needs_context")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    claims: Optional[list] = Field(default=None, description="Individual claims analyzed")
    sources: Optional[list] = Field(default=None, description="Sources and references used")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    version: str = Field(default="1.0", description="Result format version")


class BaseFactChecker(ABC):
    """Abstract base class for all fact checkers"""
    
    def __init__(self):
        if not hasattr(self, 'slug'):
            raise NotImplementedError("Fact checker must define 'slug' class attribute")
        if not hasattr(self, 'name'):
            raise NotImplementedError("Fact checker must define 'name' class attribute")
        if not hasattr(self, 'version'):
            raise NotImplementedError("Fact checker must define 'version' class attribute")
    
    @property
    @abstractmethod
    def slug(self) -> str:
        """Unique identifier for the fact checker"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Display name for the fact checker"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this fact checker does"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Version of the fact checker"""
        pass
    
    @abstractmethod
    async def fact_check(self, post_data: Dict[str, Any]) -> FactCheckResult:
        """
        Perform fact checking on a post
        
        Args:
            post_data: Dictionary containing post information including:
                - post_uid: Unique identifier for the post
                - text: The text content of the post
                - author_handle: The author of the post
                - platform: The platform the post is from
                - raw_json: Full raw data from the platform
                - classifications: Any existing classifications (optional)
        
        Returns:
            FactCheckResult with the fact check analysis
        """
        pass
    
    def get_configuration(self) -> Optional[Dict[str, Any]]:
        """
        Get configuration for this fact checker
        Can be overridden to provide custom configuration
        """
        return None
    
    async def validate_input(self, post_data: Dict[str, Any]) -> bool:
        """
        Validate that the input contains required fields
        Can be overridden for custom validation
        """
        required_fields = ['post_uid', 'text']
        return all(field in post_data for field in required_fields)