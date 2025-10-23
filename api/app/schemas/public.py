from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime


class ClassifierPublicResponse(BaseModel):
    """Public response for a classifier (read-only)"""
    classifier_id: str
    slug: str
    display_name: str
    description: Optional[str]
    group_name: Optional[str]
    is_active: bool
    output_schema: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ClassificationPublicResponse(BaseModel):
    """Public response for a classification"""
    classifier_slug: str
    classifier_display_name: str
    classifier_group: Optional[str]
    classification_type: str  # single, multi, hierarchical
    classification_data: Dict[str, Any]
    output_schema: Dict[str, Any]  # For rendering UI
    created_at: datetime
    updated_at: datetime


class NotePublicResponse(BaseModel):
    """Public response model for a community note"""
    post_uid: str
    post_text: str
    author_handle: Optional[str]
    full_body: Optional[str] = None  # Only included in detail view
    concise_body: str
    citations: List[Any]
    topic_slug: Optional[str]
    topic_display_name: Optional[str]
    submission_status: str
    submitted_at: datetime
    generated_at: datetime


class NoteListResponse(BaseModel):
    """Response model for list of notes"""
    notes: List[NotePublicResponse]
    total: int
    limit: int
    offset: int


class PostPublicResponse(BaseModel):
    """Public response model for a post (with optional note information)"""
    post_uid: str
    platform: str
    platform_post_id: str
    author_handle: Optional[str]
    text: str
    created_at: Optional[datetime]
    ingested_at: datetime
    has_note: bool
    has_fact_check: bool = False
    submission_status: Optional[str] = None
    topic_slug: Optional[str] = None
    topic_display_name: Optional[str] = None
    generated_at: Optional[datetime] = None
    # Note content (only for detail view)
    full_body: Optional[str] = None
    concise_body: Optional[str] = None
    citations: Optional[List[Any]] = None
    # Raw JSON data (for debugging)
    raw_json: Optional[Any] = None


class PostWithClassificationsResponse(PostPublicResponse):
    """Post response with classification data"""
    classifications: List[ClassificationPublicResponse] = []


class PostListResponse(BaseModel):
    """Response model for list of posts"""
    posts: List[PostWithClassificationsResponse]
    total: int
    limit: int
    offset: int


class FactCheckerPublicResponse(BaseModel):
    """Public response for a fact checker"""
    id: str
    slug: str
    name: str
    description: Optional[str]
    version: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class FactCheckPublicResponse(BaseModel):
    """Public response for a fact check"""
    id: str
    post_uid: str
    fact_checker: FactCheckerPublicResponse
    body: Optional[str]  # Markdown content for display
    raw_json: Optional[Dict[str, Any]]  # Full LangGraph output (admin only)
    verdict: Optional[str]
    confidence: Optional[float]
    claims: Optional[List[Dict[str, Any]]] = None
    status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime