"""
Introduction Pydantic Schemas

Request and response models for introduction endpoints including:
- Introduction requests and responses
- Introduction suggestions (Story 7.1)
- Match scoring
- Goal helpers and ask matchers
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict


class IntroductionRequest(BaseModel):
    """Request model for creating an introduction."""

    target_id: UUID = Field(
        ...,
        description="UUID of the founder you want to be introduced to"
    )
    message: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Personalized message explaining why you want this introduction"
    )
    connector_id: Optional[UUID] = Field(
        None,
        description="Optional UUID of a mutual connection to facilitate the introduction"
    )
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional additional context (e.g., shared goals, interests)"
    )

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message is not empty or just whitespace."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "target_id": "123e4567-e89b-12d3-a456-426614174000",
                "message": "I'd love to connect about scaling B2B SaaS products. I saw your post about PLG strategies and think we could share valuable insights.",
                "connector_id": None,
                "context": {
                    "shared_goals": ["product_market_fit", "fundraising"],
                    "reason": "complementary_expertise"
                }
            }
        }
    }


class IntroductionResponseRequest(BaseModel):
    """Request model for responding to an introduction."""

    accept: bool = Field(
        ...,
        description="True to accept the introduction, False to decline"
    )
    message: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional response message"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "accept": True,
                    "message": "Thanks for reaching out! I'd be happy to connect. Let's schedule a call."
                },
                {
                    "accept": False,
                    "message": "Thanks for the interest, but I'm not looking for connections in this area right now."
                }
            ]
        }
    }


class IntroductionCompletion(BaseModel):
    """Request model for completing an introduction."""

    outcome: str = Field(
        ...,
        pattern="^(meeting_scheduled|email_exchanged|no_response|not_relevant)$",
        description="Outcome of the introduction"
    )
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional notes about the outcome"
    )

    @field_validator('outcome')
    @classmethod
    def validate_outcome(cls, v: str) -> str:
        """Validate outcome is a valid value."""
        valid_outcomes = [
            "meeting_scheduled",
            "email_exchanged",
            "no_response",
            "not_relevant"
        ]
        if v not in valid_outcomes:
            raise ValueError(f"Outcome must be one of: {', '.join(valid_outcomes)}")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "outcome": "meeting_scheduled",
                    "notes": "We scheduled a call for next Tuesday to discuss partnership opportunities."
                },
                {
                    "outcome": "email_exchanged",
                    "notes": "Had a great email exchange and shared resources."
                },
                {
                    "outcome": "no_response",
                    "notes": "Reached out but didn't get a response after 2 weeks."
                }
            ]
        }
    }


class IntroductionResponse(BaseModel):
    """Response model for introduction data."""

    id: UUID = Field(..., description="Introduction unique identifier")
    requester_id: UUID = Field(..., description="User who requested the introduction")
    target_id: UUID = Field(..., description="User being introduced to")
    connector_id: Optional[UUID] = Field(None, description="Optional mutual connector")
    status: str = Field(..., description="Current status of the introduction")
    requester_message: str = Field(..., description="Introduction request message")
    response_message: Optional[str] = Field(None, description="Response message from target")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    outcome: Optional[str] = Field(None, description="Completion outcome if completed")
    outcome_notes: Optional[str] = Field(None, description="Notes about the outcome")
    requested_at: datetime = Field(..., description="When introduction was requested")
    responded_at: Optional[datetime] = Field(None, description="When target responded")
    completed_at: Optional[datetime] = Field(None, description="When introduction was completed")
    expires_at: datetime = Field(..., description="When introduction expires if not responded")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "requester_id": "223e4567-e89b-12d3-a456-426614174000",
                "target_id": "323e4567-e89b-12d3-a456-426614174000",
                "connector_id": None,
                "status": "accepted",
                "requester_message": "I'd love to connect about scaling B2B SaaS products.",
                "response_message": "Happy to connect! Let's schedule a call.",
                "context": {"shared_goals": ["product_market_fit"]},
                "outcome": None,
                "outcome_notes": None,
                "requested_at": "2025-12-13T10:00:00",
                "responded_at": "2025-12-13T14:30:00",
                "completed_at": None,
                "expires_at": "2025-12-20T10:00:00",
                "created_at": "2025-12-13T10:00:00",
                "updated_at": "2025-12-13T14:30:00"
            }
        }
    }


class IntroductionListResponse(BaseModel):
    """Response model for list of introductions."""

    introductions: list[IntroductionResponse] = Field(
        ...,
        description="List of introductions"
    )
    total: int = Field(..., description="Total count of introductions")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Pagination offset")

    model_config = {
        "json_schema_extra": {
            "example": {
                "introductions": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "requester_id": "223e4567-e89b-12d3-a456-426614174000",
                        "target_id": "323e4567-e89b-12d3-a456-426614174000",
                        "status": "pending",
                        "requester_message": "I'd love to connect...",
                        "requested_at": "2025-12-13T10:00:00",
                        "expires_at": "2025-12-20T10:00:00"
                    }
                ],
                "total": 1,
                "limit": 20,
                "offset": 0
            }
        }
    }


# Story 7.1 - Introduction Suggestion Schemas


class MatchScore(BaseModel):
    """
    Multi-dimensional match quality score.

    Components:
    - relevance_score: Semantic similarity of goals/asks (0-1)
    - trust_score: Profile quality and reputation (0-1)
    - reciprocity_score: Mutual value potential (0-1)
    - overall_score: Weighted combination (0-1)
    """
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Semantic similarity of goals and asks"
    )
    trust_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Profile quality and user reputation"
    )
    reciprocity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Mutual value and collaboration potential"
    )
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weighted overall match quality"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "relevance_score": 0.85,
                "trust_score": 0.75,
                "reciprocity_score": 0.80,
                "overall_score": 0.81
            }
        }
    )


class IntroductionSuggestion(BaseModel):
    """
    A single introduction suggestion with match details.

    Contains target user information, match scores, reasoning,
    and specific matching goals/asks.
    """
    target_user_id: UUID = Field(
        ...,
        description="UUID of the suggested user to connect with"
    )
    target_name: str = Field(
        ...,
        description="Name of the suggested user"
    )
    target_headline: Optional[str] = Field(
        None,
        description="Professional headline of the suggested user"
    )
    target_location: Optional[str] = Field(
        None,
        description="Location of the suggested user"
    )
    match_score: MatchScore = Field(
        ...,
        description="Multi-dimensional match quality scores"
    )
    reasoning: str = Field(
        ...,
        description="Human-readable explanation of why this is a good match"
    )
    matching_goals: List[str] = Field(
        default_factory=list,
        description="List of matching goal descriptions (max 3)"
    )
    matching_asks: List[str] = Field(
        default_factory=list,
        description="List of matching ask descriptions (max 3)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "target_user_id": "123e4567-e89b-12d3-a456-426614174000",
                "target_name": "Jane Founder",
                "target_headline": "CEO at AI Startup | Ex-Google",
                "target_location": "San Francisco, CA",
                "match_score": {
                    "relevance_score": 0.85,
                    "trust_score": 0.75,
                    "reciprocity_score": 0.80,
                    "overall_score": 0.81
                },
                "reasoning": "Working on similar goals: Build AI-powered marketplace platform. Background: CEO at AI Startup | Ex-Google. Based in San Francisco, CA.",
                "matching_goals": [
                    "Raise $2M seed round",
                    "Build AI-powered marketplace"
                ],
                "matching_asks": [
                    "Intros to tier 1 VCs in SF"
                ]
            }
        }
    )


class GoalHelper(BaseModel):
    """
    A user who can help with a specific goal.
    """
    user_id: UUID = Field(..., description="Helper user ID")
    name: Optional[str] = Field(None, description="Helper name")
    headline: Optional[str] = Field(None, description="Helper headline")
    similarity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score with goal"
    )
    reason: str = Field(..., description="Why this person can help")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "456e7890-e89b-12d3-a456-426614174001",
                "name": "Bob Expert",
                "headline": "VP Engineering at SaaS Co",
                "similarity": 0.88,
                "reason": "Has experience with: Building scalable SaaS platforms"
            }
        }
    )


class AskMatcher(BaseModel):
    """
    A user who can fulfill an ask.
    """
    user_id: UUID = Field(..., description="Matcher user ID")
    name: Optional[str] = Field(None, description="Matcher name")
    headline: Optional[str] = Field(None, description="Matcher headline")
    similarity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score with ask"
    )
    reason: str = Field(..., description="Why this person is a good match")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "789e0123-e89b-12d3-a456-426614174002",
                "name": "Alice Investor",
                "headline": "Partner at Seed VC Fund",
                "similarity": 0.92,
                "reason": "Expertise in: Seed stage investing in B2B SaaS"
            }
        }
    )
