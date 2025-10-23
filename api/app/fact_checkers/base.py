from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .shared.enums import VERDICT_LITERALS

class FactCheckResult(BaseModel):
    """Standard output format for all fact checkers"""
    body: str = Field(..., description="Full markdown-formatted fact check content")
    verdict: VERDICT_LITERALS = Field(..., description="Overall verdict for the post")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    claims: Optional[list] = Field(default=None, description="Individual claims analyzed")
    sources: Optional[list] = Field(default=None, description="Sources and references used")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    version: str = Field(default="1.0", description="Result format version")
    raw_output: Optional[Dict[str, Any]] = Field(default=None, description="Raw LangGraph agent state/output")


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
    async def should_run(self, post_data: Dict[str, Any], classifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Determine if this fact checker should run based on post data and classifications.
        This is called BEFORE the fact checker's own eligibility check.
        
        Args:
            post_data: Dictionary containing post information
            classifications: List of classification results with structure:
                - classifier_slug: The classifier that produced this result
                - classification_data: The classification data (type, value/values, etc.)
                - created_at: When the classification was created
        
        Returns:
            Dictionary with at minimum:
                - should_run: bool indicating if fact checker should run
                - reason: str explaining the decision
            Additional fields can be added in the future.
        """
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
    
    async def stream_fact_check(self, post_data: Dict[str, Any]):
        """
        Stream fact check updates as they become available.
        
        Default implementation calls fact_check() and yields the result once.
        Override this method to implement real streaming for LangGraph or other
        streaming fact checkers.
        
        Args:
            post_data: Dictionary containing post information
        
        Yields:
            Dict with update information including verdict, summary, confidence, etc.
        """
        # Default implementation: run fact_check and yield result once
        result = await self.fact_check(post_data)
        
        # Convert FactCheckResult to streaming format
        yield {
            "verdict": result.verdict,
            "body": result.body,
            "confidence": result.confidence,
            "is_eligible": True,  # Assume eligible if we got this far
            "eligibility_reason": None,
            "metadata": result.metadata,
            "raw_output": result.raw_output,
            "claims": result.claims,
            "sources": result.sources,
        }