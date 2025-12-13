"""
Advisor Agent Schemas
Pydantic models for advisor agent data validation
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, UUID4
from app.models.advisor_agent import AgentStatus, MemoryType


class AgentMemoryCreate(BaseModel):
    """Agent memory creation schema"""
    memory_type: MemoryType = Field(..., description="Type of memory")
    content: str = Field(..., min_length=1, max_length=10000, description="Memory content")
    summary: Optional[str] = Field(None, max_length=500, description="Short summary")
    confidence: int = Field(default=100, ge=0, le=100, description="Confidence score 0-100")
    source_type: Optional[str] = Field(None, max_length=50, description="Source type")
    source_id: Optional[UUID4] = Field(None, description="Reference to source entity")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")


class AgentMemoryResponse(BaseModel):
    """Agent memory response schema"""
    id: UUID4
    agent_id: UUID4
    memory_type: MemoryType
    content: str
    summary: Optional[str] = None
    embedding_id: Optional[str] = None
    confidence: int
    source_type: Optional[str] = None
    source_id: Optional[UUID4] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AdvisorAgentCreate(BaseModel):
    """Advisor agent creation schema (internal use)"""
    name: str = Field(default="Advisor", max_length=255, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")


class AdvisorAgentUpdate(BaseModel):
    """Advisor agent update schema"""
    name: Optional[str] = Field(None, max_length=255, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    is_enabled: Optional[bool] = Field(None, description="Enable/disable agent")


class AdvisorAgentResponse(BaseModel):
    """Advisor agent response schema"""
    id: UUID4
    user_id: UUID4
    status: AgentStatus
    name: str
    description: Optional[str] = None
    memory_namespace: Optional[str] = None
    total_memories: int
    last_memory_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None
    last_summary_at: Optional[datetime] = None
    total_suggestions: int
    total_actions: int
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentSuggestion(BaseModel):
    """Suggestion from advisor agent"""
    suggestion_type: str = Field(..., description="Type of suggestion (introduction, goal, action)")
    title: str = Field(..., description="Brief title")
    description: str = Field(..., description="Detailed description")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score 0-1")
    rationale: str = Field(..., description="Why this suggestion was made")
    related_entities: List[UUID4] = Field(default=[], description="Related entity IDs")
    metadata: dict = Field(default={}, description="Additional metadata")


class WeeklyOpportunitySummary(BaseModel):
    """Weekly opportunity summary from advisor agent"""
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    total_opportunities: int
    suggestions: List[AgentSuggestion]
    highlights: List[str] = Field(default=[], description="Key highlights")
    metrics: dict = Field(default={}, description="Summary metrics")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentActionRequest(BaseModel):
    """Request for agent to perform an action"""
    action_type: str = Field(..., description="Type of action to perform")
    target_id: Optional[UUID4] = Field(None, description="Target entity ID")
    parameters: dict = Field(default={}, description="Action parameters")
    requires_approval: bool = Field(default=True, description="Requires user approval")


class AgentActionResponse(BaseModel):
    """Response from agent action"""
    action_id: UUID4
    status: str = Field(..., description="pending, approved, executed, rejected")
    result: Optional[dict] = Field(None, description="Action result if executed")
    message: str = Field(..., description="Status message")
