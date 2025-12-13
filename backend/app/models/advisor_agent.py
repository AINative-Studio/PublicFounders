"""
Advisor Agent Enums
Enums for advisor agent status and memory types.
NoSQL data is stored in ZeroDB, not SQLAlchemy.
"""
import enum


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
