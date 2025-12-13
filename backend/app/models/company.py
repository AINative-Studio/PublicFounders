"""
Company model for founder organizations.
Tracks company information and stages.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class CompanyStage(str, PyEnum):
    """Company development stages."""
    IDEA = "idea"
    PRE_SEED = "pre-seed"
    SEED = "seed"
    SERIES_A = "series-a"
    SERIES_B_PLUS = "series-b+"


class Company(Base):
    """
    Companies table - organizations founded or operated by users.

    Business Rules:
    - Company can have multiple founders/team members
    - Stage progression tracked over time
    - Industry for matching and categorization
    - Company embeddings enable semantic search
    """
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    stage = Column(Enum(CompanyStage), nullable=False, index=True)
    industry = Column(String(255), nullable=True, index=True)
    website = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Embedding tracking
    embedding_id = Column(String(255), nullable=True, index=True)
    embedding_updated_at = Column(DateTime, nullable=True)

    # Relationships
    company_roles = relationship("CompanyRole", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Company {self.id} - {self.name} ({self.stage.value})>"

    @property
    def embedding_content(self) -> str:
        """Generate content for semantic embedding."""
        parts = [
            self.name,
            f"Stage: {self.stage.value}",
        ]
        if self.industry:
            parts.append(f"Industry: {self.industry}")
        if self.description:
            parts.append(self.description)
        return " | ".join(parts)

    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "stage": self.stage.value,
            "industry": self.industry,
            "website": self.website,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
