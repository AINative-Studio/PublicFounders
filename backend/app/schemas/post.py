"""
Pydantic schemas for Post CRUD operations.
Handles build-in-public feed content.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from app.models.post import PostType


class PostBase(BaseModel):
    """Base schema for post data."""
    type: PostType = Field(..., description="Type of post content")
    content: str = Field(..., min_length=10, max_length=5000, description="Post content")
    is_cross_posted: bool = Field(default=False, description="Whether to cross-post to LinkedIn")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Ensure content is meaningful."""
        if not v or v.strip() == "":
            raise ValueError("Content cannot be empty")
        return v.strip()


class PostCreate(PostBase):
    """Schema for creating a new post."""
    pass


class PostUpdate(BaseModel):
    """Schema for updating an existing post."""
    type: Optional[PostType] = None
    content: Optional[str] = Field(None, min_length=10, max_length=5000)
    is_cross_posted: Optional[bool] = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: Optional[str]) -> Optional[str]:
        """Ensure content is meaningful if provided."""
        if v is not None and v.strip() == "":
            raise ValueError("Content cannot be empty")
        return v.strip() if v else None


class PostResponse(PostBase):
    """Schema for post responses."""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    embedding_status: str
    embedding_created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "type": "milestone",
                "content": "Just closed our first enterprise customer! $50k ARR. This validates our pricing model.",
                "is_cross_posted": True,
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T10:30:00Z",
                "embedding_status": "completed",
                "embedding_created_at": "2025-01-15T10:30:05Z"
            }
        }


class PostListResponse(BaseModel):
    """Schema for paginated post list."""
    posts: list[PostResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class PostDiscoveryRequest(BaseModel):
    """Schema for semantic discovery requests."""
    limit: int = Field(default=20, ge=1, le=100, description="Number of posts to retrieve")
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")
    recency_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight for recency in ranking (0-1)")


class PostDiscoveryResponse(BaseModel):
    """Schema for semantic discovery results."""
    posts: list[PostResponse]
    similarity_scores: list[float]
    total: int
