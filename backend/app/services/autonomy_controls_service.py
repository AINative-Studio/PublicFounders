"""
Autonomy Controls Service - Story 9.1
Ensures agent actions always check autonomy mode before execution.
Uses ZeroDB NoSQL for audit logging.

This service provides:
1. Permission checking based on user's autonomy mode
2. Execution wrapper that enforces permission checks
3. Audit logging for all permission checks
4. @require_permission decorator for easy integration
"""
import uuid
import logging
from datetime import datetime
from typing import Callable, Dict, Any, Tuple, List, Optional
from functools import wraps

from app.core.enums import AutonomyMode
from app.models.advisor_agent import AgentStatus
from app.services.zerodb_client import zerodb_client

logger = logging.getLogger(__name__)


class PermissionDeniedError(Exception):
    """Raised when an agent action is blocked due to autonomy controls."""
    pass


# Global service instance for decorator use
_autonomy_service_instance: Optional['AutonomyControlsService'] = None


def get_autonomy_service() -> 'AutonomyControlsService':
    """Get or create the global autonomy service instance."""
    global _autonomy_service_instance
    if _autonomy_service_instance is None:
        _autonomy_service_instance = AutonomyControlsService()
    return _autonomy_service_instance


def require_permission(action_type: str):
    """
    Decorator to require permission check before executing agent action.

    The decorated function must have 'agent_id' as its first parameter.

    Args:
        action_type: Type of action ("suggest" or "act")

    Raises:
        PermissionDeniedError: If permission is denied

    Example:
        @require_permission("suggest")
        async def make_suggestion(agent_id: uuid.UUID):
            return {"suggestion": "Consider connecting with John"}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(agent_id: uuid.UUID, *args, **kwargs):
            service = get_autonomy_service()
            allowed, reason = await service.check_permission(agent_id, action_type)

            # Log the permission check
            await service._log_audit(
                agent_id=agent_id,
                action_type=action_type,
                allowed=allowed,
                reason=reason
            )

            if not allowed:
                raise PermissionDeniedError(reason)

            return await func(agent_id, *args, **kwargs)
        return wrapper
    return decorator


class AutonomyControlsService:
    """
    Service for enforcing agent autonomy controls.

    Ensures all agent actions check the user's autonomy mode
    before execution, providing safety and user control.

    Features:
    - Permission checking based on autonomy mode (suggest, approve, auto)
    - Agent status validation (active, paused, disabled)
    - Audit logging of all permission checks
    - Execution wrapper for enforced permission checks
    - Decorator for easy integration with existing code

    Data Storage:
    - Audit logs: ZeroDB NoSQL table 'autonomy_audit_log'
    """

    # Autonomy mode descriptions for user education
    AUTONOMY_MODE_DESCRIPTIONS = {
        AutonomyMode.SUGGEST: (
            "Suggest mode: Your AI advisor can make suggestions but cannot "
            "take actions on your behalf. You maintain full control."
        ),
        AutonomyMode.APPROVE: (
            "Approve mode: Your AI advisor can make suggestions and propose "
            "actions, but requires your explicit approval before acting."
        ),
        AutonomyMode.AUTO: (
            "Auto mode: Your AI advisor can take autonomous actions on your "
            "behalf based on learned preferences. Use with caution."
        ),
    }

    def __init__(self, audit_enabled: bool = True):
        """
        Initialize the autonomy controls service.

        Args:
            audit_enabled: Whether to log permission checks (default True)
        """
        self.zerodb_client = zerodb_client
        self.audit_enabled = audit_enabled

    async def check_permission(
        self,
        agent_id: uuid.UUID,
        action_type: str
    ) -> Tuple[bool, str]:
        """
        Check if agent has permission to perform action based on user's autonomy mode.

        Args:
            agent_id: Agent UUID
            action_type: Type of action ("suggest" or "act")

        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        agent_id_str = str(agent_id)

        # Get agent
        agent = await self.zerodb_client.get_by_id("advisor_agents", agent_id_str)
        if not agent:
            return False, "Agent not found"

        # Check if agent is enabled
        if not agent.get("is_enabled", False):
            return False, "Agent is disabled"

        # Check agent status
        status = agent.get("status")
        if status != AgentStatus.ACTIVE.value:
            return False, f"Agent is not active (status: {status})"

        # Get user's founder profile for autonomy mode
        user_id = agent.get("user_id")
        profiles = await self.zerodb_client.query_rows(
            table_name="founder_profiles",
            filter={"user_id": user_id},
            limit=1
        )

        if not profiles:
            return False, "Founder profile not found"

        profile = profiles[0]
        autonomy_mode = profile.get("autonomy_mode", AutonomyMode.SUGGEST.value)

        # Check permission based on action type and autonomy mode
        if action_type == "suggest":
            # Suggestions are allowed in all modes
            if autonomy_mode in (
                AutonomyMode.SUGGEST.value,
                AutonomyMode.APPROVE.value,
                AutonomyMode.AUTO.value
            ):
                return True, "Suggestions allowed"
            return False, f"Suggestions not allowed in {autonomy_mode} mode"

        if action_type == "act":
            # Autonomous actions only allowed in auto mode
            if autonomy_mode == AutonomyMode.AUTO.value:
                return True, "Autonomous action allowed"
            return False, f"Autonomous action not allowed in {autonomy_mode} mode"

        return False, f"Unknown action type: {action_type}"

    async def execute_with_permission_check(
        self,
        agent_id: uuid.UUID,
        action_type: str,
        action_fn: Callable
    ) -> Dict[str, Any]:
        """
        Execute an action with permission check and audit logging.

        This is the primary method for ensuring all agent actions
        go through permission checks.

        Args:
            agent_id: Agent UUID
            action_type: Type of action ("suggest" or "act")
            action_fn: Callable that performs the action

        Returns:
            Dict with keys:
                - success: Whether the action succeeded
                - permission_checked: Always True (confirmation)
                - blocked: True if permission was denied
                - reason: Reason for the permission decision
                - action_result: Result of action_fn (if allowed)
        """
        # Check permission
        allowed, reason = await self.check_permission(agent_id, action_type)

        # Get autonomy mode for audit log
        autonomy_mode = await self._get_autonomy_mode(agent_id)

        # Log the permission check
        await self._log_audit(
            agent_id=agent_id,
            action_type=action_type,
            allowed=allowed,
            reason=reason,
            autonomy_mode=autonomy_mode
        )

        result = {
            "success": allowed,
            "permission_checked": True,
            "blocked": not allowed,
            "reason": reason,
        }

        if allowed:
            # Execute the action
            try:
                action_result = action_fn()
                result["action_result"] = action_result
            except Exception as e:
                logger.error(f"Action execution failed for agent {agent_id}: {e}")
                result["success"] = False
                result["error"] = str(e)
        else:
            result["action_result"] = None

        return result

    async def _get_autonomy_mode(self, agent_id: uuid.UUID) -> Optional[str]:
        """Get autonomy mode for an agent's user."""
        agent = await self.zerodb_client.get_by_id("advisor_agents", str(agent_id))
        if not agent:
            return None

        user_id = agent.get("user_id")
        profiles = await self.zerodb_client.query_rows(
            table_name="founder_profiles",
            filter={"user_id": user_id},
            limit=1
        )

        if profiles:
            return profiles[0].get("autonomy_mode")
        return None

    async def _log_audit(
        self,
        agent_id: uuid.UUID,
        action_type: str,
        allowed: bool,
        reason: str,
        autonomy_mode: Optional[str] = None
    ) -> None:
        """
        Log permission check to audit trail.

        Args:
            agent_id: Agent UUID
            action_type: Type of action checked
            allowed: Whether permission was granted
            reason: Reason for the decision
            autonomy_mode: User's autonomy mode at time of check
        """
        if not self.audit_enabled:
            return

        audit_entry = {
            "id": str(uuid.uuid4()),
            "agent_id": str(agent_id),
            "action_type": action_type,
            "allowed": allowed,
            "reason": reason,
            "autonomy_mode": autonomy_mode or "unknown",
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            await self.zerodb_client.insert_rows("autonomy_audit_log", [audit_entry])
            logger.debug(
                f"Audit log: agent={agent_id} action={action_type} "
                f"allowed={allowed} mode={autonomy_mode}"
            )
        except Exception as e:
            logger.warning(f"Failed to log audit entry: {e}")
            # Don't fail the action just because audit logging failed

    async def get_audit_history(
        self,
        agent_id: uuid.UUID,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get audit history for an agent.

        Args:
            agent_id: Agent UUID
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries, newest first
        """
        entries = await self.zerodb_client.query_rows(
            table_name="autonomy_audit_log",
            filter={"agent_id": str(agent_id)},
            limit=limit,
            sort={"timestamp": -1}
        )
        return entries

    def get_autonomy_mode_description(self, mode: AutonomyMode) -> str:
        """
        Get human-readable description of an autonomy mode.

        Args:
            mode: The autonomy mode

        Returns:
            Description string for the mode
        """
        return self.AUTONOMY_MODE_DESCRIPTIONS.get(
            mode,
            f"Unknown autonomy mode: {mode}"
        )

    def get_all_autonomy_modes(self) -> List[AutonomyMode]:
        """
        Get all available autonomy modes.

        Returns:
            List of all AutonomyMode enum values
        """
        return [AutonomyMode.SUGGEST, AutonomyMode.APPROVE, AutonomyMode.AUTO]


# Singleton instance
autonomy_controls_service = AutonomyControlsService()
