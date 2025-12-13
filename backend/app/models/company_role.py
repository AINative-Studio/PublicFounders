"""
CompanyRole model for user-company relationships.
Tracks roles, current status, and tenure.
"""
import uuid
from datetime import datetime, date
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class CompanyRole(Base):
    """
    CompanyRoles table - links users to companies with role information.

    Business Rules:
    - Each user can have multiple company roles (founder, advisor, employee)
    - Only one active "current" role per company (is_current = True)
    - Historical roles preserved with start/end dates
    - Used for founder/operator matching and credibility
    """
    __tablename__ = "company_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(255), nullable=False)  # e.g., "Founder", "CEO", "CTO", "Advisor"
    is_current = Column(Boolean, default=True, nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="company_roles")
    company = relationship("Company", back_populates="company_roles")

    def __repr__(self) -> str:
        status = "current" if self.is_current else "past"
        return f"<CompanyRole {self.id} - {self.role} at {self.company_id} ({status})>"

    def mark_ended(self, end_date: date = None) -> None:
        """Mark role as ended with optional end date."""
        self.is_current = False
        self.end_date = end_date or date.today()

    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "company_id": str(self.company_id),
            "role": self.role,
            "is_current": self.is_current,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
