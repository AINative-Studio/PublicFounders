"""
User Schemas
Pydantic models for user data validation
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, UUID4


class LinkedInUserData(BaseModel):
    """LinkedIn OAuth user data"""
    linkedin_id: str = Field(..., description="LinkedIn user ID")
    name: str = Field(..., min_length=1, max_length=255, description="Full name")
    headline: Optional[str] = Field(None, max_length=500, description="Professional headline")
    profile_photo_url: Optional[str] = Field(None, description="Profile photo URL")
    location: Optional[str] = Field(None, max_length=255, description="Location")
    email: Optional[EmailStr] = Field(None, description="Email address")


class UserCreate(BaseModel):
    """User creation schema"""
    linkedin_id: str
    name: str
    headline: Optional[str] = None
    profile_photo_url: Optional[str] = None
    location: Optional[str] = None
    email: Optional[EmailStr] = None


class UserUpdate(BaseModel):
    """User update schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    headline: Optional[str] = Field(None, max_length=500)
    profile_photo_url: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    """User response schema"""
    id: UUID4
    linkedin_id: str
    name: str
    headline: Optional[str] = None
    profile_photo_url: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    phone_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
