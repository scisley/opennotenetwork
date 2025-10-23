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




class ReconcileResponse(BaseModel):
    """Response from reconciliation"""
    checked: int
    updated: int
    unchanged: int


class SubmissionDetail(BaseModel):
    """Detailed submission information"""
    submission_id: str
    note_id: str
    x_note_id: Optional[str]
    status: str
    submitted_at: datetime
    submitted_by: Optional[str]
    status_updated_at: Optional[datetime]
    response_json: Optional[Dict[str, Any]]
    status_json: Optional[Dict[str, Any]]
    submission_errors: Optional[Dict[str, Any]]
    status_errors: Optional[Dict[str, Any]]


class SubmitNoteResponse(BaseModel):
    """Response from submitting a note"""
    submission_id: str
    status: str
    x_note_id: Optional[str]
    error: Optional[str]


class UpdateStatusesResponse(BaseModel):
    """Response from updating submission statuses"""
    updated_count: int
    error_count: int
    errors: List[str]
    total_x_notes: int
    timestamp: str


class SubmissionsSummaryResponse(BaseModel):
    """Summary of all submissions"""
    status_counts: Dict[str, int]
    total: int
    last_status_update: Optional[str]


class SubmissionQueueItem(BaseModel):
    """Item in the submission queue"""
    post_uid: str
    post_text: str
    best_score: float
    note_count: int
    created_at: datetime


class SubmissionQueueResponse(BaseModel):
    """Response for submission queue endpoint"""
    items: List[SubmissionQueueItem]
    total: int


class WritingLimitResponse(BaseModel):
    """X.com daily writing limit calculation"""
    writing_limit: int = Field(..., description="Daily note writing limit")
    nh_5: int = Field(..., description="Not Helpful notes in last 5 non-NMR submissions")
    nh_10: int = Field(..., description="Not Helpful notes in last 10 non-NMR submissions")
    hr_r: float = Field(..., description="Recent hit rate: (CRH-CRNH)/Total in last 20 notes")
    hr_l: float = Field(..., description="Long-term hit rate: (CRH-CRNH)/Total in last 100 notes")
    dn_30: float = Field(..., description="Average daily notes written in last 30 days")
    total_notes: int = Field(..., description="Total notes written with X status")
    notes_without_status: int = Field(..., description="Submitted notes awaiting status from X")
    calculated_at: str = Field(..., description="Timestamp of calculation")


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
    drafts: List[Dict[str, Any]] = []
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
    draft_count: int = 0
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


# Batch Fact Check schemas
class BatchFactCheckRequest(BaseModel):
    """Request for batch fact checking"""
    start_date: datetime
    end_date: datetime
    fact_checker_slugs: Optional[List[str]] = Field(None, description="Specific fact checkers to run, or None for all active")
    force: bool = Field(False, description="Force recheck even if fact check already exists")


class BatchFactCheckResponse(BaseModel):
    """Response from initiating batch fact check"""
    job_id: str
    status: str = "started"
    message: str
    total_posts: int


class BatchFactCheckJobStatus(BaseModel):
    """Status of a batch fact check job"""
    job_id: str
    status: Literal["running", "completed", "failed"]
    total_posts: int
    processed: int
    fact_checks_triggered: int
    skipped: int
    errors: List[str]
    progress_percentage: float
    started_at: datetime
    completed_at: Optional[datetime] = None


class FactCheckEligibleCountResponse(BaseModel):
    """Response for counting eligible posts for fact checking"""
    post_count: int
    date_range: Dict[str, datetime]
    fact_checker_slugs: Optional[List[str]] = None


class EditNoteRequest(BaseModel):
    """Request to edit a note"""
    text: str
    links: Optional[List[Dict[str, str]]] = None


class NoteLink(BaseModel):
    """Link in a community note"""
    url: str


class EditNoteResponse(BaseModel):
    """Response after editing a note"""
    note_id: str
    text: str
    original_text: Optional[str]
    links: Optional[List[NoteLink]]
    original_links: Optional[List[NoteLink]]
    is_edited: bool
    status: str