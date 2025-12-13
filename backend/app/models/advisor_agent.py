"""
Advisor Agent Model
Represents persistent AI advisor agents for each founder
"""
import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class AgentStatus(str, enum.Enum):
    """Agent lifecycle status"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    DEACTIVATED = "deactivated"


class MemoryType(str, enum.Enum):
    """Types of agent memory"""
    PREFERENCE = "preference"  # User preferences learned over time
    OUTCOME = "outcome"  # Results of past actions
    CONTEXT = "context"  # Working memory for current tasks


class AdvisorAgent(Base):
    """
    AdvisorAgent model for persistent AI agents per founder

    Each founder has one advisor agent that:
    - Has isolated memory (scoped by agent_id in ZeroDB)
    - Cannot act without checking user's autonomy_mode permissions
    - Generates weekly opportunity summaries
    - Learns from interaction outcomes
    """
    __tablename__ = "advisor_agents"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Owner relationship
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One agent per founder
        index=True
    )

    # Agent Status
    status = Column(SQLEnum(AgentStatus), default=AgentStatus.INITIALIZING, nullable=False, index=True)

    # Agent Identity
    name = Column(String(255), default="Advisor", nullable=False)
    description = Column(Text, nullable=True)

    # Memory tracking (ZeroDB references)
    memory_namespace = Column(String(255), nullable=True)  # ZeroDB namespace for this agent's memory
    total_memories = Column(Integer, default=0, nullable=False)
    last_memory_at = Column(DateTime, nullable=True)

    # Activity tracking
    last_active_at = Column(DateTime, nullable=True)
    last_summary_at = Column(DateTime, nullable=True)  # When last weekly summary was generated
    total_suggestions = Column(Integer, default=0, nullable=False)
    total_actions = Column(Integer, default=0, nullable=False)

    # Configuration
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="advisor_agent")
    memories = relationship(
        "AgentMemory",
        back_populates="agent",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AdvisorAgent(id={self.id}, user_id={self.user_id}, status={self.status})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "status": self.status.value,
            "name": self.name,
            "description": self.description,
            "memory_namespace": self.memory_namespace,
            "total_memories": self.total_memories,
            "last_memory_at": self.last_memory_at.isoformat() if self.last_memory_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "last_summary_at": self.last_summary_at.isoformat() if self.last_summary_at else None,
            "total_suggestions": self.total_suggestions,
            "total_actions": self.total_actions,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def can_act_autonomously(self, autonomy_mode: str) -> bool:
        """Check if agent can act without user approval based on autonomy mode"""
        if not self.is_enabled or self.status != AgentStatus.ACTIVE:
            return False
        return autonomy_mode == "auto"

    def can_suggest(self, autonomy_mode: str) -> bool:
        """Check if agent can make suggestions"""
        if not self.is_enabled or self.status != AgentStatus.ACTIVE:
            return False
        return autonomy_mode in ("suggest", "approve", "auto")

    def activate(self) -> None:
        """Activate the agent"""
        self.status = AgentStatus.ACTIVE
        self.last_active_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the agent"""
        self.status = AgentStatus.DEACTIVATED

    def record_suggestion(self) -> None:
        """Record that agent made a suggestion"""
        self.total_suggestions += 1
        self.last_active_at = datetime.utcnow()

    def record_action(self) -> None:
        """Record that agent took an action"""
        self.total_actions += 1
        self.last_active_at = datetime.utcnow()


class AgentMemory(Base):
    """
    AgentMemory model for storing agent memory records

    These are the relational references to vector embeddings stored in ZeroDB.
    Provides auditability while semantic search happens in vector store.
    """
    __tablename__ = "agent_memories"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Agent relationship
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("advisor_agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Memory content
    memory_type = Column(SQLEnum(MemoryType), nullable=False, index=True)
    content = Column(Text, nullable=False)
    summary = Column(String(500), nullable=True)  # Short summary for quick reference

    # ZeroDB reference
    embedding_id = Column(String(255), nullable=True, index=True)  # Vector ID in ZeroDB

    # Metadata
    confidence = Column(Integer, default=100, nullable=False)  # 0-100 confidence score
    source_type = Column(String(50), nullable=True)  # What generated this memory (intro, feedback, etc.)
    source_id = Column(UUID(as_uuid=True), nullable=True)  # Reference to source entity

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # For time-decaying memories

    # Relationships
    agent = relationship("AdvisorAgent", back_populates="memories")

    def __repr__(self) -> str:
        return f"<AgentMemory(id={self.id}, agent_id={self.agent_id}, type={self.memory_type})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "memory_type": self.memory_type.value,
            "content": self.content,
            "summary": self.summary,
            "embedding_id": self.embedding_id,
            "confidence": self.confidence,
            "source_type": self.source_type,
            "source_id": str(self.source_id) if self.source_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @property
    def embedding_content(self) -> str:
        """Generate content for semantic embedding"""
        return f"{self.memory_type.value}: {self.content}"

    def is_expired(self) -> bool:
        """Check if memory has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
