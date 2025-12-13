"""
Introduction model for AI-driven founder connections.
Tracks intro suggestions, execution, and outcomes.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class IntroductionChannel(str, PyEnum):
    """Communication channels for introductions."""
    LINKEDIN = "linkedin"
    SMS = "sms"
    EMAIL = "email"


class IntroductionStatus(str, PyEnum):
    """Lifecycle status for introductions."""
    PROPOSED = "proposed"  # Agent suggested, waiting approval
    SENT = "sent"  # Introduction sent
    ACCEPTED = "accepted"  # Target accepted intro
    DECLINED = "declined"  # Target declined intro
    SUCCESSFUL = "successful"  # Positive outcome recorded
    FAILED = "failed"  # Negative outcome or no response


class Introduction(Base):
    """
    Introductions table - AI-driven founder connections.

    Business Rules:
    - Requester is the founder seeking connection
    - Target is the person being introduced to
    - Agent can propose intros based on autonomy mode
    - Rationale stored for transparency and learning
    - Status progresses through lifecycle
    - Outcomes tracked separately for RLHF
    """
    __tablename__ = "introductions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    requester_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_initiated = Column(Boolean, default=True, nullable=False, index=True)
    channel = Column(Enum(IntroductionChannel), nullable=False, index=True)
    rationale = Column(Text, nullable=False)  # Why agent suggested this intro
    status = Column(Enum(IntroductionStatus), default=IntroductionStatus.PROPOSED, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)

    # Embedding tracking for similarity matching
    embedding_id = Column(String(255), nullable=True, index=True)
    embedding_updated_at = Column(DateTime, nullable=True)

    # Relationships
    requester = relationship("User", foreign_keys=[requester_id], back_populates="requested_introductions")
    target = relationship("User", foreign_keys=[target_id], back_populates="received_introductions")
    outcomes = relationship("InteractionOutcome", back_populates="introduction", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Introduction {self.id} - {self.status.value} via {self.channel.value}>"

    @property
    def embedding_content(self) -> str:
        """Generate content for semantic embedding."""
        return f"Introduction rationale: {self.rationale}"

    def mark_sent(self) -> None:
        """Mark introduction as sent."""
        self.status = IntroductionStatus.SENT
        self.sent_at = datetime.utcnow()

    def mark_accepted(self) -> None:
        """Mark introduction as accepted by target."""
        self.status = IntroductionStatus.ACCEPTED
        self.responded_at = datetime.utcnow()

    def mark_declined(self) -> None:
        """Mark introduction as declined by target."""
        self.status = IntroductionStatus.DECLINED
        self.responded_at = datetime.utcnow()

    def mark_successful(self) -> None:
        """Mark introduction as successful with positive outcome."""
        self.status = IntroductionStatus.SUCCESSFUL

    def mark_failed(self) -> None:
        """Mark introduction as failed."""
        self.status = IntroductionStatus.FAILED

    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "requester_id": str(self.requester_id),
            "target_id": str(self.target_id),
            "agent_initiated": self.agent_initiated,
            "channel": self.channel.value,
            "rationale": self.rationale,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
        }
