from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict, Literal
from datetime import datetime
import uuid


class IngestResponse(BaseModel):
    """Response from ingestion endpoint"""
    added: int
    skipped: int
    classified: Optional[int] = 0
    errors: List[str]
    classification_errors: Optional[List[Dict[str, Any]]] = []


class TopicLabel(BaseModel):
    """Topic classification result"""
    topic_slug: str
    confidence: Optional[float]
    labeled_by: str


class ClassifyRequest(BaseModel):
    """Request to rerun classification"""
    version: Optional[str] = None


class ClassifyResponse(BaseModel):
    """Response from classification"""
    post_uid: str
    topics: List[TopicLabel]
    classifier_version: str


class GenerateDraftRequest(BaseModel):
    """Request to generate draft note"""
    topic_slug: Optional[str] = None
    regenerate: bool = False


class GenerateDraftResponse(BaseModel):
    """Response from draft generation"""
    draft_id: str
    post_uid: str
    full_body: str
    concise_body: str
    citations: List[Any]
    generator_version: str


class EditDraftRequest(BaseModel):
    """Request to edit draft"""
    full_body: Optional[str] = None
    concise_body: Optional[str] = None
    citations: Optional[List[Any]] = None


class SubmissionResponse(BaseModel):
    """Response from submission"""
    submission_id: str
    x_note_id: Optional[str]
    status: str


class ReconcileResponse(BaseModel):
    """Response from reconciliation"""
    checked: int
    updated: int
    unchanged: int


class DraftDetail(BaseModel):
    """Detailed draft information"""
    draft_id: str
    full_body: str
    concise_body: str
    citations: Optional[List[Any]]
    status: str
    generated_at: datetime
    generator_version: Optional[str]


class SubmissionDetail(BaseModel):
    """Detailed submission information"""
    submission_id: str
    x_note_id: Optional[str]
    status: str
    submitted_at: datetime


class PostDetailResponse(BaseModel):
    """Detailed post information for admin"""
    post_uid: str
    platform: str
    platform_post_id: str
    author_handle: Optional[str]
    text: str
    created_at: Optional[datetime]
    ingested_at: datetime
    last_error: Optional[str]
    topics: List[Dict[str, Any]]
    drafts: List[Dict[str, Any]]
    submissions: List[Dict[str, Any]]


class AdminPostResponse(BaseModel):
    """Post response for admin lists"""
    post_uid: str
    platform: str
    platform_post_id: str
    author_handle: Optional[str]
    text: str
    ingested_at: datetime
    classified_at: Optional[datetime]
    last_error: Optional[str]
    topic_count: int
    draft_count: int
    submission_count: int


# Classifier schemas
class ClassifierOutputSchema(BaseModel):
    """Schema describing classifier output format"""
    type: Literal["single", "multi", "hierarchical"]
    name: str
    description: str
    choices: Optional[List[Dict[str, Any]]] = None
    max_selections: Optional[int] = None
    levels: Optional[List[Dict[str, Any]]] = None
    supports_confidence: bool = True


class ClassifierBase(BaseModel):
    """Base classifier fields"""
    slug: str = Field(..., description="Unique identifier for classifier")
    display_name: str
    description: Optional[str] = None
    group_name: Optional[str] = None
    is_active: bool = True
    output_schema: Dict[str, Any]
    config: Optional[Dict[str, Any]] = {}


class ClassifierCreate(ClassifierBase):
    """Request to create a classifier"""
    pass


class ClassifierUpdate(BaseModel):
    """Request to update a classifier"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    group_name: Optional[str] = None
    is_active: Optional[bool] = None
    output_schema: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None


class ClassifierResponse(ClassifierBase):
    """Classifier response"""
    classifier_id: str
    created_at: datetime
    updated_at: datetime
    classification_count: Optional[int] = 0


class ClassifierListResponse(BaseModel):
    """List of classifiers"""
    classifiers: List[ClassifierResponse]
    total: int


# Classification schemas
class ClassificationData(BaseModel):
    """Classification result data"""
    type: Literal["single", "multi", "hierarchical"]
    value: Optional[str] = None
    values: Optional[List[Dict[str, Any]]] = None
    levels: Optional[List[Dict[str, Any]]] = None
    confidence: Optional[float] = None


class ClassificationCreate(BaseModel):
    """Request to create a classification"""
    post_uid: str
    classifier_slug: str
    classification_data: Dict[str, Any]


class ClassificationResponse(BaseModel):
    """Classification response"""
    classification_id: str
    post_uid: str
    classifier_slug: str
    classifier_display_name: Optional[str] = None
    classification_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime