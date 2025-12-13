"""
Pydantic schemas for Ask CRUD operations.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from app.models.ask import AskUrgency, AskStatus


class AskBase(BaseModel):
    """Base schema for ask data."""
    description: str = Field(..., min_length=10, max_length=2000, description="What help is needed")
    urgency: AskUrgency = Field(default=AskUrgency.MEDIUM, description="How urgent is this ask")
    goal_id: Optional[UUID] = Field(None, description="Optional linked goal")

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Ensure description is meaningful."""
        if not v or v.strip() == "":
            raise ValueError("Description cannot be empty")
        return v.strip()


class AskCreate(AskBase):
    """Schema for creating a new ask."""
    pass


class AskUpdate(BaseModel):
    """Schema for updating an existing ask."""
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    urgency: Optional[AskUrgency] = None
    goal_id: Optional[UUID] = None

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Ensure description is meaningful if provided."""
        if v is not None and v.strip() == "":
            raise ValueError("Description cannot be empty")
        return v.strip() if v else None


class AskStatusUpdate(BaseModel):
    """Schema for updating ask status."""
    status: AskStatus = Field(..., description="New status for the ask")


class AskResponse(AskBase):
    """Schema for ask responses."""
    id: UUID
    user_id: UUID
    status: AskStatus
    created_at: datetime
    updated_at: datetime
    fulfilled_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "goal_id": "123e4567-e89b-12d3-a456-426614174002",
                "description": "Looking for introductions to seed investors in fintech space",
                "urgency": "high",
                "status": "open",
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T10:30:00Z",
                "fulfilled_at": None
            }
        }


class AskListResponse(BaseModel):
    """Schema for paginated ask list."""
    asks: list[AskResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
