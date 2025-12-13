"""
Core enums used across the application
These are defined separately to avoid circular imports
"""
import enum


class AutonomyMode(str, enum.Enum):
    """Agent autonomy modes"""
    SUGGEST = "suggest"  # Agent suggests, user approves
    APPROVE = "approve"  # Agent acts, user can override
    AUTO = "auto"  # Agent acts autonomously
