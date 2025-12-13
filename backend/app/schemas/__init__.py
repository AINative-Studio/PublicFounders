"""
Pydantic Schemas for Request/Response Validation
"""
from app.schemas.user import (
    UserResponse,
    UserCreate,
    UserUpdate,
    LinkedInUserData
)
from app.schemas.founder_profile import (
    FounderProfileResponse,
    FounderProfileCreate,
    FounderProfileUpdate
)
from app.schemas.auth import (
    Token,
    TokenData,
    PhoneVerificationRequest,
    PhoneVerificationConfirm
)
from app.schemas.advisor_agent import (
    AdvisorAgentCreate,
    AdvisorAgentUpdate,
    AdvisorAgentResponse,
    AgentMemoryCreate,
    AgentMemoryResponse,
    AgentSuggestion,
    WeeklyOpportunitySummary,
    AgentActionRequest,
    AgentActionResponse
)
from app.schemas.introduction import (
    IntroductionRequest,
    IntroductionResponseRequest,
    IntroductionCompletion,
    IntroductionResponse,
    IntroductionListResponse
)

__all__ = [
    "UserResponse",
    "UserCreate",
    "UserUpdate",
    "LinkedInUserData",
    "FounderProfileResponse",
    "FounderProfileCreate",
    "FounderProfileUpdate",
    "Token",
    "TokenData",
    "PhoneVerificationRequest",
    "PhoneVerificationConfirm",
    "AdvisorAgentCreate",
    "AdvisorAgentUpdate",
    "AdvisorAgentResponse",
    "AgentMemoryCreate",
    "AgentMemoryResponse",
    "AgentSuggestion",
    "WeeklyOpportunitySummary",
    "AgentActionRequest",
    "AgentActionResponse",
    "IntroductionRequest",
    "IntroductionResponseRequest",
    "IntroductionCompletion",
    "IntroductionResponse",
    "IntroductionListResponse",
]
