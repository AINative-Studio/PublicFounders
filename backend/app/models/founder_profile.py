"""
Founder Profile Model
Extended profile information for founders
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class AutonomyMode(str, enum.Enum):
    """Agent autonomy modes"""
    SUGGEST = "suggest"  # Agent suggests, user approves
    APPROVE = "approve"  # Agent acts, user can override
    AUTO = "auto"  # Agent acts autonomously


class FounderProfile(Base):
    """
    Founder profile with bio, focus, and preferences
    One-to-one relationship with User
    """
    __tablename__ = "founder_profiles"

    # Primary Key (same as user_id)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )

    # Profile Content
    bio = Column(Text, nullable=True)
    current_focus = Column(Text, nullable=True)

    # Agent Preferences
    autonomy_mode = Column(
        SQLEnum(AutonomyMode),
        default=AutonomyMode.SUGGEST,
        nullable=False
    )

    # Visibility Settings
    public_visibility = Column(Boolean, default=True, nullable=False)

    # Embedding Metadata
    embedding_id = Column(String(255), nullable=True, index=True)  # ZeroDB vector ID
    embedding_updated_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="founder_profile")

    def __repr__(self) -> str:
        return f"<FounderProfile(user_id={self.user_id}, autonomy_mode='{self.autonomy_mode}')>"

    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "user_id": str(self.user_id),
            "bio": self.bio,
            "current_focus": self.current_focus,
            "autonomy_mode": self.autonomy_mode.value if self.autonomy_mode else None,
            "public_visibility": self.public_visibility,
            "embedding_id": self.embedding_id,
            "embedding_updated_at": self.embedding_updated_at.isoformat() if self.embedding_updated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
