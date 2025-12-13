"""
Founder Profile Schemas
Pydantic models for founder profile data validation
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, UUID4
from app.models.founder_profile import AutonomyMode


class FounderProfileCreate(BaseModel):
    """Founder profile creation schema"""
    bio: Optional[str] = Field(None, max_length=5000, description="Founder bio")
    current_focus: Optional[str] = Field(None, max_length=2000, description="Current focus/goals")
    autonomy_mode: AutonomyMode = Field(
        default=AutonomyMode.SUGGEST,
        description="Agent autonomy mode"
    )
    public_visibility: bool = Field(default=True, description="Profile visibility")


class FounderProfileUpdate(BaseModel):
    """Founder profile update schema"""
    bio: Optional[str] = Field(None, max_length=5000, description="Founder bio")
    current_focus: Optional[str] = Field(None, max_length=2000, description="Current focus/goals")
    autonomy_mode: Optional[AutonomyMode] = Field(None, description="Agent autonomy mode")
    public_visibility: Optional[bool] = Field(None, description="Profile visibility")


class FounderProfileResponse(BaseModel):
    """Founder profile response schema"""
    user_id: UUID4
    bio: Optional[str] = None
    current_focus: Optional[str] = None
    autonomy_mode: AutonomyMode
    public_visibility: bool
    embedding_id: Optional[str] = None
    embedding_updated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
