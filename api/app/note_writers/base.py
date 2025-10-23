from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field


class NoteResult(BaseModel):
    """Standard output format for all note writers"""
    text: str = Field(..., description="The actual note text")
    links: list[dict[str, str]] = Field(default=[], description="List of links with url field")
    submission_json: dict[str, Any] = Field(..., description="JSON formatted for platform submission")
    raw_output: Optional[dict[str, Any]] = Field(default=None, description="Full state/output for debugging (e.g., LangGraph state)")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Additional metadata")
    version: str = Field(default="1.0", description="Result format version")


class BaseNoteWriter(ABC):
    """Abstract base class for all note writers"""

    def __init__(self):
        if not hasattr(self, 'slug'):
            raise NotImplementedError("Note writer must define 'slug' class attribute")
        if not hasattr(self, 'name'):
            raise NotImplementedError("Note writer must define 'name' class attribute")
        if not hasattr(self, 'version'):
            raise NotImplementedError("Note writer must define 'version' class attribute")
        if not hasattr(self, 'platforms'):
            raise NotImplementedError("Note writer must define 'platforms' class attribute")

    @property
    @abstractmethod
    def slug(self) -> str:
        """Unique identifier for the note writer"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name for the note writer"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this note writer does"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Version of the note writer"""
        pass

    @property
    @abstractmethod
    def platforms(self) -> list[str]:
        """List of platform IDs this writer supports"""
        pass

    @abstractmethod
    async def write_note(self, post_data: dict[str, Any], fact_check_data: dict[str, Any]) -> NoteResult:
        """
        Write a note based on post data and fact check data

        Args:
            post_data: Dictionary containing post information including:
                - post_uid: Unique identifier for the post
                - text: The text content of the post
                - author_handle: The author of the post
                - platform: The platform the post is from
                - raw_json: Full raw data from the platform
            fact_check_data: Dictionary containing fact check information including:
                - summary: The fact check summary text
                - verdict: The fact check verdict
                - confidence: The confidence score
                - fact_check_id: The fact check ID
                - status: The fact check status

        Returns:
            NoteResult with the written note
        """
        pass

    def get_configuration(self) -> Optional[dict[str, Any]]:
        """
        Get configuration for this note writer
        Can be overridden to provide custom configuration
        """
        return None

    async def validate_input(self, post_data: dict[str, Any], fact_check_data: dict[str, Any]) -> bool:
        """
        Validate that the input contains required fields
        Can be overridden for custom validation
        """
        required_post_fields = ['post_uid', 'text', 'platform']
        required_fact_check_fields = ['body', 'verdict']
        return (all(field in post_data for field in required_post_fields) and
                all(field in fact_check_data for field in required_fact_check_fields))
