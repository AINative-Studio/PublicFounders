"""
Outcome Pydantic Schemas

Request and response models for introduction outcome tracking including:
- Outcome recording and updates
- Outcome analytics and statistics
- RLHF integration for learning

Story 8.1: Record Intro Outcome
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


class OutcomeType(str, Enum):
    """Introduction outcome types."""
    SUCCESSFUL = "successful"
    UNSUCCESSFUL = "unsuccessful"
    NO_RESPONSE = "no_response"
    NOT_RELEVANT = "not_relevant"


class OutcomeCreate(BaseModel):
    """Request model for creating an introduction outcome."""

    outcome_type: OutcomeType = Field(
        ...,
        description="Type of outcome: successful, unsuccessful, no_response, not_relevant"
    )
    feedback_text: Optional[str] = Field(
        None,
        min_length=10,
        max_length=500,
        description="Optional detailed feedback about the outcome (10-500 chars)"
    )
    rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Optional rating from 1 (poor) to 5 (excellent)"
    )
    tags: Optional[List[str]] = Field(
        None,
        max_length=10,
        description="Optional tags for categorization (max 10 tags)"
    )

    @field_validator('feedback_text')
    @classmethod
    def validate_feedback_text(cls, v: Optional[str]) -> Optional[str]:
        """Validate feedback text is not empty or just whitespace."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Feedback text cannot be empty or whitespace")
        return v

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate tags are not empty and normalized."""
        if v is not None:
            validated_tags = []
            for tag in v:
                tag = tag.strip().lower()
                if not tag:
                    raise ValueError("Tags cannot be empty or whitespace")
                if len(tag) > 50:
                    raise ValueError("Individual tag cannot exceed 50 characters")
                validated_tags.append(tag)
            return validated_tags
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "outcome_type": "successful",
                    "feedback_text": "Had a great conversation! We're scheduling a follow-up to discuss partnership opportunities.",
                    "rating": 5,
                    "tags": ["partnership", "follow-up", "valuable"]
                },
                {
                    "outcome_type": "unsuccessful",
                    "feedback_text": "The introduction didn't lead to anything actionable, but it was a pleasant exchange.",
                    "rating": 3,
                    "tags": ["not-actionable"]
                },
                {
                    "outcome_type": "no_response",
                    "feedback_text": "Sent a message but haven't received a response after two weeks.",
                    "rating": None,
                    "tags": ["unresponsive"]
                }
            ]
        }
    )


class OutcomeUpdate(BaseModel):
    """Request model for updating an existing outcome."""

    outcome_type: Optional[OutcomeType] = Field(
        None,
        description="Updated outcome type"
    )
    feedback_text: Optional[str] = Field(
        None,
        min_length=10,
        max_length=500,
        description="Updated feedback text (10-500 chars)"
    )
    rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Updated rating (1-5)"
    )
    tags: Optional[List[str]] = Field(
        None,
        max_length=10,
        description="Updated tags (max 10)"
    )

    @field_validator('feedback_text')
    @classmethod
    def validate_feedback_text(cls, v: Optional[str]) -> Optional[str]:
        """Validate feedback text is not empty or just whitespace."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Feedback text cannot be empty or whitespace")
        return v

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate tags are not empty and normalized."""
        if v is not None:
            validated_tags = []
            for tag in v:
                tag = tag.strip().lower()
                if not tag:
                    raise ValueError("Tags cannot be empty or whitespace")
                if len(tag) > 50:
                    raise ValueError("Individual tag cannot exceed 50 characters")
                validated_tags.append(tag)
            return validated_tags
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "outcome_type": "successful",
                "feedback_text": "Updated after our second meeting - we're moving forward with collaboration!",
                "rating": 5,
                "tags": ["collaboration", "partnership", "committed"]
            }
        }
    )


class OutcomeResponse(BaseModel):
    """Response model for outcome data."""

    id: UUID = Field(..., description="Outcome unique identifier")
    introduction_id: UUID = Field(..., description="Associated introduction ID")
    user_id: UUID = Field(..., description="User who recorded the outcome")
    outcome_type: str = Field(..., description="Type of outcome")
    feedback_text: Optional[str] = Field(None, description="Detailed feedback")
    rating: Optional[int] = Field(None, description="Rating 1-5")
    tags: List[str] = Field(default_factory=list, description="Outcome tags")
    created_at: datetime = Field(..., description="When outcome was created")
    updated_at: datetime = Field(..., description="When outcome was last updated")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "introduction_id": "223e4567-e89b-12d3-a456-426614174000",
                "user_id": "323e4567-e89b-12d3-a456-426614174000",
                "outcome_type": "successful",
                "feedback_text": "Had a great conversation! We're scheduling a follow-up meeting.",
                "rating": 5,
                "tags": ["partnership", "follow-up", "valuable"],
                "created_at": "2025-12-13T10:00:00",
                "updated_at": "2025-12-13T10:00:00"
            }
        }
    )


class OutcomeStats(BaseModel):
    """Statistics for a specific outcome type."""

    outcome_type: str = Field(..., description="Outcome type")
    count: int = Field(..., description="Number of outcomes of this type")
    percentage: float = Field(..., description="Percentage of total outcomes")
    avg_rating: Optional[float] = Field(None, description="Average rating for this outcome type")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "outcome_type": "successful",
                "count": 15,
                "percentage": 60.0,
                "avg_rating": 4.7
            }
        }
    )


class OutcomeAnalytics(BaseModel):
    """Analytics response model for user's outcome data."""

    user_id: UUID = Field(..., description="User ID")
    total_outcomes: int = Field(..., description="Total number of outcomes recorded")
    outcome_breakdown: List[OutcomeStats] = Field(
        ...,
        description="Breakdown by outcome type"
    )
    average_rating: Optional[float] = Field(
        None,
        description="Overall average rating across all outcomes"
    )
    top_tags: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Most frequently used tags with counts"
    )
    success_rate: float = Field(
        ...,
        description="Percentage of successful outcomes"
    )
    response_rate: float = Field(
        ...,
        description="Percentage of outcomes that received responses (successful + unsuccessful)"
    )
    period_start: Optional[datetime] = Field(
        None,
        description="Start of analytics period"
    )
    period_end: Optional[datetime] = Field(
        None,
        description="End of analytics period"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "total_outcomes": 25,
                "outcome_breakdown": [
                    {
                        "outcome_type": "successful",
                        "count": 15,
                        "percentage": 60.0,
                        "avg_rating": 4.7
                    },
                    {
                        "outcome_type": "unsuccessful",
                        "count": 5,
                        "percentage": 20.0,
                        "avg_rating": 3.2
                    },
                    {
                        "outcome_type": "no_response",
                        "count": 3,
                        "percentage": 12.0,
                        "avg_rating": None
                    },
                    {
                        "outcome_type": "not_relevant",
                        "count": 2,
                        "percentage": 8.0,
                        "avg_rating": 2.5
                    }
                ],
                "average_rating": 4.3,
                "top_tags": [
                    {"tag": "partnership", "count": 8},
                    {"tag": "follow-up", "count": 6},
                    {"tag": "valuable", "count": 5}
                ],
                "success_rate": 60.0,
                "response_rate": 80.0,
                "period_start": None,
                "period_end": None
            }
        }
    )
