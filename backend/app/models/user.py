"""
User Model
Represents authenticated users in the system
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    """
    User model for authentication and identity management
    Primary source: LinkedIn OAuth
    """
    __tablename__ = "users"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # LinkedIn OAuth Data
    linkedin_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    headline = Column(String(500), nullable=True)
    profile_photo_url = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)

    # Contact Information
    email = Column(String(255), nullable=True, unique=True, index=True)
    phone_number = Column(String(20), nullable=True, unique=True, index=True)
    phone_verified = Column(Boolean, default=False, nullable=False)
    phone_verification_code = Column(String(10), nullable=True)
    phone_verification_expires_at = Column(DateTime, nullable=True)

    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    founder_profile = relationship(
        "FounderProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    company_roles = relationship(
        "CompanyRole",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    goals = relationship(
        "Goal",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    asks = relationship(
        "Ask",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    posts = relationship(
        "Post",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    requested_introductions = relationship(
        "Introduction",
        foreign_keys="Introduction.requester_id",
        back_populates="requester",
        cascade="all, delete-orphan"
    )
    received_introductions = relationship(
        "Introduction",
        foreign_keys="Introduction.target_id",
        back_populates="target",
        cascade="all, delete-orphan"
    )
    # Note: AdvisorAgent data is stored in ZeroDB, not SQLAlchemy

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}', linkedin_id='{self.linkedin_id}')>"

    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "linkedin_id": self.linkedin_id,
            "name": self.name,
            "headline": self.headline,
            "profile_photo_url": self.profile_photo_url,
            "location": self.location,
            "email": self.email,
            "phone_number": self.phone_number,
            "phone_verified": self.phone_verified,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
