from sqlalchemy import Column, String, Text, TIMESTAMP, UUID, Numeric, Boolean, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid


Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    clerk_user_id = Column(String, unique=True, nullable=True)  # Clerk's user ID (e.g., user_abc123)
    display_name = Column(String)
    role = Column(String, nullable=False, default="viewer")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint("role IN ('admin','viewer')", name="check_user_role"),
    )


class Platform(Base):
    __tablename__ = "platforms"
    
    platform_id = Column(String, primary_key=True)
    display_name = Column(String, nullable=False)
    config = Column(JSONB)
    status = Column(String, nullable=False, default="active")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("status IN ('active','archived')", name="check_platform_status"),
    )


class Post(Base):
    __tablename__ = "posts"
    
    post_uid = Column(String, primary_key=True)
    platform = Column(String, ForeignKey("platforms.platform_id"), nullable=False)
    platform_post_id = Column(String, nullable=False)
    author_handle = Column(String)
    text = Column(Text, nullable=False)
    raw_json = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True))
    ingested_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    last_error = Column(Text)
    classified_at = Column(TIMESTAMP(timezone=True))
    
    # Relationships
    platform_ref = relationship("Platform")
    post_topics = relationship("PostTopic", back_populates="post", cascade="all, delete-orphan")
    classifications = relationship("Classification", back_populates="post", cascade="all, delete-orphan")
    draft_notes = relationship("DraftNote", back_populates="post", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="post", cascade="all, delete-orphan")
    fact_checks = relationship("FactCheck", back_populates="post", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("split_part(post_uid, '--', 1) = platform", name="post_uid_platform_consistent"),
        Index("idx_posts_platform_platform_id", "platform", "platform_post_id"),
    )


class Topic(Base):
    __tablename__ = "topics"
    
    topic_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    config = Column(JSONB)
    status = Column(String, nullable=False, default="active")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    post_topics = relationship("PostTopic", back_populates="topic", cascade="all, delete-orphan")
    draft_notes = relationship("DraftNote", back_populates="topic")
    
    __table_args__ = (
        CheckConstraint("status IN ('active','archived')", name="check_topic_status"),
    )


class PostTopic(Base):
    __tablename__ = "post_topics"
    
    post_uid = Column(String, ForeignKey("posts.post_uid", ondelete="CASCADE"), primary_key=True)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.topic_id", ondelete="CASCADE"), primary_key=True)
    labeled_by = Column(String, nullable=False)
    confidence = Column(Numeric(3, 2))
    classifier_version = Column(String)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    post = relationship("Post", back_populates="post_topics")
    topic = relationship("Topic", back_populates="post_topics")
    
    __table_args__ = (
        CheckConstraint("labeled_by IN ('classifier','admin')", name="check_labeled_by"),
        Index("idx_post_topics_post", "post_uid"),
        Index("idx_post_topics_topic", "topic_id"),
    )


class Classifier(Base):
    __tablename__ = "classifiers"
    
    classifier_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(Text)
    group_name = Column(String)
    is_active = Column(Boolean, nullable=False, default=True)
    output_schema = Column(JSONB, nullable=False)
    config = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    classifications = relationship("Classification", back_populates="classifier", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_classifiers_group", "group_name"),
        Index("idx_classifiers_active", "is_active"),
    )


class Classification(Base):
    __tablename__ = "classifications"
    
    classification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_uid = Column(String, ForeignKey("posts.post_uid", ondelete="CASCADE"), nullable=False)
    classifier_slug = Column(String, ForeignKey("classifiers.slug", ondelete="CASCADE"), nullable=False)
    classification_data = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    post = relationship("Post", back_populates="classifications")
    classifier = relationship("Classifier", back_populates="classifications")
    
    __table_args__ = (
        Index("idx_classifications_post", "post_uid"),
        Index("idx_classifications_classifier", "classifier_slug"),
        Index("idx_classifications_post_classifier", "post_uid", "classifier_slug", unique=True),
    )


class DraftNote(Base):
    __tablename__ = "draft_notes"
    
    draft_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_uid = Column(String, ForeignKey("posts.post_uid", ondelete="CASCADE"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.topic_id"))
    full_body = Column(Text, nullable=False)
    concise_body = Column(Text, nullable=False)
    citations = Column(JSONB)
    generator_version = Column(String)
    generated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    regenerated_from = Column(UUID(as_uuid=True), ForeignKey("draft_notes.draft_id"))
    draft_status = Column(String, nullable=False, default="draft")
    edited_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    edited_at = Column(TIMESTAMP(timezone=True))
    
    # Relationships
    post = relationship("Post", back_populates="draft_notes")
    topic = relationship("Topic", back_populates="draft_notes")
    editor = relationship("User")
    regenerated_from_note = relationship("DraftNote", remote_side="DraftNote.draft_id")
    submissions = relationship("Submission", back_populates="draft")
    
    __table_args__ = (
        CheckConstraint("draft_status IN ('draft','approved','submitted','superseded')", name="check_draft_status"),
        Index("idx_draft_notes_post", "post_uid"),
        # Removed unique constraint on post_uid to allow multiple notes per post
    )


class Submission(Base):
    __tablename__ = "submissions"
    
    submission_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_uid = Column(String, ForeignKey("posts.post_uid", ondelete="CASCADE"), nullable=False)
    draft_id = Column(UUID(as_uuid=True), ForeignKey("draft_notes.draft_id"), nullable=False, unique=True)
    x_note_id = Column(String)
    submission_status = Column(String, nullable=False, default="submitted")
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    submitted_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    response_json = Column(JSONB)
    
    # Relationships
    post = relationship("Post", back_populates="submissions")
    draft = relationship("DraftNote", back_populates="submissions")
    submitter = relationship("User")
    
    __table_args__ = (
        CheckConstraint("submission_status IN ('submitted','accepted','rejected','unknown')", name="check_submission_status"),
        Index("idx_submissions_post", "post_uid"),
        Index("idx_submissions_status", "submission_status"),
    )


class FactChecker(Base):
    __tablename__ = "fact_checkers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(String(50), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    configuration = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    fact_checks = relationship("FactCheck", back_populates="fact_checker", cascade="all, delete-orphan")


class FactCheck(Base):
    __tablename__ = "fact_checks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_uid = Column(String(255), ForeignKey("posts.post_uid", ondelete="CASCADE"), nullable=False)
    fact_checker_id = Column(UUID(as_uuid=True), ForeignKey("fact_checkers.id"), nullable=False)
    result = Column(JSONB, nullable=False)
    verdict = Column(String(50))
    confidence = Column(Numeric(3, 2))
    check_metadata = Column("metadata", JSONB)  # Use different Python name but same DB column
    status = Column(String(50), nullable=False, default="pending")
    error_message = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    post = relationship("Post", back_populates="fact_checks")
    fact_checker = relationship("FactChecker", back_populates="fact_checks")
    
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="check_confidence_range"),
        CheckConstraint("status IN ('pending','processing','completed','failed')", name="check_fact_check_status"),
        CheckConstraint("verdict IN ('true','false','misleading','unverifiable','needs_context')", name="check_verdict_values"),
        Index("idx_fact_checks_post_uid", "post_uid"),
        Index("idx_fact_checks_fact_checker_id", "fact_checker_id"),
        Index("idx_fact_checks_verdict", "verdict"),
        Index("idx_fact_checks_status", "status"),
        Index("idx_fact_checks_created_at", "created_at"),
        Index("idx_fact_checks_post_checker", "post_uid", "fact_checker_id", unique=True),
    )