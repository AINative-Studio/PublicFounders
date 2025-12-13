"""
Pydantic schemas for Goal CRUD operations.
Handles request validation and response serialization.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from app.models.goal import GoalType


class GoalBase(BaseModel):
    """Base schema for goal data."""
    type: GoalType = Field(..., description="Category of the goal")
    description: str = Field(..., min_length=10, max_length=2000, description="Detailed goal description")
    priority: int = Field(default=1, ge=1, le=10, description="Priority level (1-10)")
    is_active: bool = Field(default=True, description="Whether goal is currently active")

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Ensure description is meaningful."""
        if not v or v.strip() == "":
            raise ValueError("Description cannot be empty")
        return v.strip()


class GoalCreate(GoalBase):
    """Schema for creating a new goal."""
    pass


class GoalUpdate(BaseModel):
    """Schema for updating an existing goal."""
    type: Optional[GoalType] = None
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    priority: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Ensure description is meaningful if provided."""
        if v is not None and v.strip() == "":
            raise ValueError("Description cannot be empty")
        return v.strip() if v else None


class GoalResponse(GoalBase):
    """Schema for goal responses."""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "type": "fundraising",
                "description": "Raise $2M seed round by Q2 2025 to scale our SaaS platform",
                "priority": 10,
                "is_active": True,
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T10:30:00Z"
            }
        }


class GoalListResponse(BaseModel):
    """Schema for paginated goal list."""
    goals: list[GoalResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
