"""
Goal model for intent capture.
Represents founder goals with semantic embedding support.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class GoalType(str, PyEnum):
    """Goal categories for founders."""
    FUNDRAISING = "fundraising"
    HIRING = "hiring"
    GROWTH = "growth"
    PARTNERSHIPS = "partnerships"
    LEARNING = "learning"


class Goal(Base):
    """
    Goals table - captures founder intent.
    
    Business Rules:
    - Each goal must belong to a user
    - Goals can be active or inactive
    - Priority determines importance (higher = more important)
    - Goal embeddings created automatically on save
    """
    __tablename__ = "goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(Enum(GoalType), nullable=False, index=True)
    description = Column(Text, nullable=False)
    priority = Column(Integer, default=1, nullable=False)  # 1-10 scale
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="goals")
    asks = relationship("Ask", back_populates="goal", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Goal {self.id} - {self.type.value}: {self.description[:50]}>"

    @property
    def embedding_content(self) -> str:
        """Generate content for semantic embedding."""
        return f"{self.type.value}: {self.description}"
