"""
InteractionOutcome model for tracking introduction results.
Critical for RLHF and agent improvement.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class OutcomeType(str, PyEnum):
    """Types of outcomes from introductions."""
    MEETING = "meeting"  # Meeting scheduled/completed
    INVESTMENT = "investment"  # Investment discussion or deal
    HIRE = "hire"  # Hiring discussion or offer
    PARTNERSHIP = "partnership"  # Partnership formed
    NONE = "none"  # No meaningful outcome


class InteractionOutcome(Base):
    """
    InteractionOutcomes table - tracks results from introductions.

    Business Rules:
    - Each outcome linked to exactly one introduction
    - Outcome type determines success metric
    - Notes capture qualitative feedback
    - Used for RLHF to improve agent matching
    - Outcomes update embeddings for better future matching
    """
    __tablename__ = "interaction_outcomes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    introduction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("introductions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One outcome per introduction
        index=True
    )
    outcome_type = Column(Enum(OutcomeType), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Embedding tracking for outcome patterns
    embedding_id = Column(String(255), nullable=True, index=True)
    embedding_updated_at = Column(DateTime, nullable=True)

    # Relationships
    introduction = relationship("Introduction", back_populates="outcomes")

    def __repr__(self) -> str:
        return f"<InteractionOutcome {self.id} - {self.outcome_type.value} for intro {self.introduction_id}>"

    @property
    def embedding_content(self) -> str:
        """Generate content for semantic embedding."""
        parts = [f"Outcome: {self.outcome_type.value}"]
        if self.notes:
            parts.append(self.notes)
        return " | ".join(parts)

    @property
    def is_successful(self) -> bool:
        """Determine if outcome represents success."""
        return self.outcome_type in [
            OutcomeType.MEETING,
            OutcomeType.INVESTMENT,
            OutcomeType.HIRE,
            OutcomeType.PARTNERSHIP
        ]

    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "introduction_id": str(self.introduction_id),
            "outcome_type": self.outcome_type.value,
            "notes": self.notes,
            "is_successful": self.is_successful,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
