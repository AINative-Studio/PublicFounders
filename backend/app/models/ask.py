"""
Ask model for specific help requests.
Links to goals and tracks fulfillment status.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class AskUrgency(str, PyEnum):
    """Urgency levels for asks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AskStatus(str, PyEnum):
    """Lifecycle status for asks."""
    OPEN = "open"
    FULFILLED = "fulfilled"
    CLOSED = "closed"


class Ask(Base):
    """
    Asks table - specific help requests from founders.
    
    Business Rules:
    - Must belong to a user
    - Can optionally link to a goal
    - Status lifecycle: open -> fulfilled/closed
    - Urgency affects agent prioritization
    - Ask embeddings enable semantic matching
    """
    __tablename__ = "asks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="SET NULL"), nullable=True, index=True)
    description = Column(Text, nullable=False)
    urgency = Column(Enum(AskUrgency), default=AskUrgency.MEDIUM, nullable=False, index=True)
    status = Column(Enum(AskStatus), default=AskStatus.OPEN, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    fulfilled_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="asks")
    goal = relationship("Goal", back_populates="asks")

    def __repr__(self) -> str:
        return f"<Ask {self.id} - {self.urgency.value}/{self.status.value}: {self.description[:50]}>"

    @property
    def embedding_content(self) -> str:
        """Generate content for semantic embedding."""
        urgency_prefix = f"[{self.urgency.value.upper()}] " if self.urgency != AskUrgency.MEDIUM else ""
        return f"{urgency_prefix}{self.description}"

    def mark_fulfilled(self) -> None:
        """Mark ask as fulfilled with timestamp."""
        self.status = AskStatus.FULFILLED
        self.fulfilled_at = datetime.utcnow()

    def mark_closed(self) -> None:
        """Mark ask as closed without fulfillment."""
        self.status = AskStatus.CLOSED
