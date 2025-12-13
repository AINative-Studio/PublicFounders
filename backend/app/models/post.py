"""
Post model for build-in-public feed.
Supports async embedding to avoid blocking user experience.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class PostType(str, PyEnum):
    """Content types for posts."""
    PROGRESS = "progress"
    LEARNING = "learning"
    MILESTONE = "milestone"
    ASK = "ask"


class Post(Base):
    """
    Posts table - build-in-public feed content.
    
    Business Rules:
    - Must belong to a user
    - Can be cross-posted to LinkedIn
    - Embeddings created asynchronously (don't block post creation)
    - Posts ordered chronologically in feed
    - Semantic ranking for discovery
    """
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(Enum(PostType), nullable=False, index=True)
    content = Column(Text, nullable=False)
    is_cross_posted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Embedding tracking
    embedding_status = Column(
        Enum("pending", "processing", "completed", "failed", name="embedding_status_enum"),
        default="pending",
        nullable=False
    )
    embedding_created_at = Column(DateTime, nullable=True)
    embedding_error = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="posts")

    def __repr__(self) -> str:
        return f"<Post {self.id} - {self.type.value}: {self.content[:50]}>"

    @property
    def embedding_content(self) -> str:
        """Generate content for semantic embedding."""
        type_prefix = f"[{self.type.value.upper()}] "
        return f"{type_prefix}{self.content}"

    def mark_embedding_completed(self) -> None:
        """Mark embedding as successfully created."""
        self.embedding_status = "completed"
        self.embedding_created_at = datetime.utcnow()
        self.embedding_error = None

    def mark_embedding_failed(self, error: str) -> None:
        """Mark embedding creation as failed with error message."""
        self.embedding_status = "failed"
        self.embedding_error = error
