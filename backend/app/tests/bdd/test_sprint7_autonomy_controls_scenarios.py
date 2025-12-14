"""
BDD Scenarios for Sprint 7: Autonomy Controls (Story 9.1)
Behavior-Driven Development tests for agent autonomy enforcement
Uses ZeroDB NoSQL + Vectors (not PostgreSQL)

Story 9.1: Autonomy Controls
As a founder, I want to control agent autonomy, So that I feel safe

TDD Acceptance Test: Agent actions always check autonomy mode
"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from app.models.advisor_agent import AgentStatus, MemoryType
from app.core.enums import AutonomyMode


@pytest.mark.bdd
class TestStory9_1_AgentActionsAlwaysCheckAutonomyMode:
    """
    Story 9.1: Autonomy Controls
    As a founder, I want to control agent autonomy
    So that I feel safe

    TDD Acceptance Test: Agent actions always check autonomy mode
    """

    @pytest.mark.asyncio
    async def test_scenario_suggest_action_checks_autonomy_before_execution(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Suggest action checks autonomy before execution
        Given I have an active advisor agent
        And my autonomy mode is "suggest"
        When the agent attempts to make a suggestion
        Then the autonomy check is performed BEFORE the suggestion
        And the suggestion is allowed to proceed
        """
        from app.services.autonomy_controls_service import AutonomyControlsService

        # Given: I have an active advisor agent with autonomy mode "suggest"
        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AutonomyControlsService()

        # When: The agent attempts to make a suggestion
        result = await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_fn=lambda: {"suggestion": "Connect with John"}
        )

        # Then: The autonomy check is performed and suggestion is allowed
        assert result["success"] is True
        assert result["permission_checked"] is True
        assert result["action_result"] == {"suggestion": "Connect with John"}

    @pytest.mark.asyncio
    async def test_scenario_act_action_blocked_in_suggest_mode(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Autonomous action blocked in suggest mode
        Given I have an active advisor agent
        And my autonomy mode is "suggest"
        When the agent attempts to take an autonomous action
        Then the autonomy check is performed
        And the action is blocked
        And the reason is "autonomous action not allowed"
        """
        from app.services.autonomy_controls_service import AutonomyControlsService

        # Given: My autonomy mode is "suggest"
        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        agent["status"] = AgentStatus.ACTIVE.value

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AutonomyControlsService()

        # When: The agent attempts to take an autonomous action
        result = await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="act",
            action_fn=lambda: {"action": "Send intro email"}
        )

        # Then: The action is blocked
        assert result["success"] is False
        assert result["permission_checked"] is True
        assert result["blocked"] is True
        assert "not allowed" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_scenario_act_action_allowed_in_auto_mode(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Autonomous action allowed in auto mode
        Given I have an active advisor agent
        And my autonomy mode is "auto"
        When the agent attempts to take an autonomous action
        Then the autonomy check is performed
        And the action is allowed to proceed
        """
        from app.services.autonomy_controls_service import AutonomyControlsService

        # Given: My autonomy mode is "auto"
        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.AUTO.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AutonomyControlsService()

        # When: The agent attempts to take an autonomous action
        result = await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="act",
            action_fn=lambda: {"action": "Sent intro email automatically"}
        )

        # Then: The action is allowed
        assert result["success"] is True
        assert result["permission_checked"] is True
        assert result["action_result"] == {"action": "Sent intro email automatically"}

    @pytest.mark.asyncio
    async def test_scenario_action_blocked_when_agent_disabled(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: All actions blocked when agent is disabled
        Given I have disabled my advisor agent
        When the agent attempts any action
        Then the autonomy check is performed
        And all actions are blocked
        And the reason mentions "disabled"
        """
        from app.services.autonomy_controls_service import AutonomyControlsService

        # Given: I have disabled my advisor agent
        user, profile, agent = sample_user_with_profile_and_agent_dict
        agent["is_enabled"] = False

        mock_zerodb_client.get_by_id.return_value = agent

        service = AutonomyControlsService()

        # When: The agent attempts any action
        result = await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_fn=lambda: {"suggestion": "This should not happen"}
        )

        # Then: The action is blocked
        assert result["success"] is False
        assert result["permission_checked"] is True
        assert result["blocked"] is True
        assert "disabled" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_scenario_action_blocked_when_agent_paused(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: All actions blocked when agent is paused
        Given my agent is paused
        When the agent attempts any action
        Then the autonomy check is performed
        And all actions are blocked
        """
        from app.services.autonomy_controls_service import AutonomyControlsService

        # Given: My agent is paused
        user, profile, agent = sample_user_with_profile_and_agent_dict
        agent["status"] = AgentStatus.PAUSED.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent

        service = AutonomyControlsService()

        # When: The agent attempts any action
        result = await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="act",
            action_fn=lambda: {"action": "This should be blocked"}
        )

        # Then: The action is blocked
        assert result["success"] is False
        assert result["blocked"] is True
        assert "not active" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_scenario_approve_mode_requires_user_confirmation(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Approve mode requires user confirmation for actions
        Given my autonomy mode is "approve"
        When the agent wants to act
        Then suggestions are allowed
        But autonomous actions require approval
        """
        from app.services.autonomy_controls_service import AutonomyControlsService

        # Given: My autonomy mode is "approve"
        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.APPROVE.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AutonomyControlsService()

        # Suggestions should be allowed
        suggest_result = await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_fn=lambda: {"suggestion": "Consider connecting"}
        )
        assert suggest_result["success"] is True

        # Autonomous actions should require approval (blocked without it)
        act_result = await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="act",
            action_fn=lambda: {"action": "Auto send email"}
        )
        assert act_result["success"] is False
        assert "not allowed" in act_result["reason"].lower()


@pytest.mark.bdd
class TestAutonomyControlsAuditTrail:
    """
    BDD scenarios for autonomy controls audit trail
    Ensures all permission checks are logged for safety/compliance
    """

    @pytest.mark.asyncio
    async def test_scenario_permission_checks_are_logged(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Permission checks are logged for audit
        Given I have an active advisor agent
        When the agent performs any action
        Then the permission check is recorded in the audit log
        """
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AutonomyControlsService()

        await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_fn=lambda: {"suggestion": "Test"}
        )

        # Verify audit log was created
        audit_calls = [
            call for call in mock_zerodb_client.insert_rows.call_args_list
            if call.args[0] == "autonomy_audit_log"
        ]
        assert len(audit_calls) >= 1, "Permission check should be logged"

    @pytest.mark.asyncio
    async def test_scenario_blocked_actions_are_logged_with_reason(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Blocked actions are logged with reason
        Given my autonomy mode is "suggest"
        When the agent attempts an autonomous action
        Then the blocked action is logged
        And the log includes the reason for blocking
        """
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AutonomyControlsService()

        await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="act",
            action_fn=lambda: {"action": "Blocked action"}
        )

        # Verify blocked action was logged with reason
        audit_calls = [
            call for call in mock_zerodb_client.insert_rows.call_args_list
            if call.args[0] == "autonomy_audit_log"
        ]
        assert len(audit_calls) >= 1

        # Check the logged data includes blocked status and reason
        logged_data = audit_calls[0].args[1][0]
        assert logged_data["allowed"] is False
        assert "reason" in logged_data


@pytest.mark.bdd
class TestAutonomyModeTransitions:
    """
    BDD scenarios for autonomy mode transitions
    """

    @pytest.mark.asyncio
    async def test_scenario_changing_autonomy_mode_affects_permissions(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Changing autonomy mode immediately affects permissions
        Given my autonomy mode was "auto"
        When I change it to "suggest"
        Then the agent can no longer take autonomous actions
        """
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent

        service = AutonomyControlsService()

        # First, with auto mode - action should be allowed
        profile["autonomy_mode"] = AutonomyMode.AUTO.value
        mock_zerodb_client.query_rows.return_value = [profile]

        result_auto = await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="act",
            action_fn=lambda: {"action": "Auto action"}
        )
        assert result_auto["success"] is True

        # Now change to suggest mode - action should be blocked
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        mock_zerodb_client.query_rows.return_value = [profile]

        result_suggest = await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="act",
            action_fn=lambda: {"action": "Should be blocked now"}
        )
        assert result_suggest["success"] is False
        assert result_suggest["blocked"] is True


@pytest.mark.bdd
class TestRequirePermissionDecorator:
    """
    BDD scenarios for the @require_permission decorator
    Ensures all decorated actions check permissions automatically
    """

    @pytest.mark.asyncio
    async def test_scenario_decorated_function_checks_permission(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Decorated function automatically checks permission
        Given a function decorated with @require_permission("suggest")
        When the function is called
        Then permission is checked before execution
        """
        from app.services.autonomy_controls_service import (
            AutonomyControlsService,
            require_permission
        )

        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AutonomyControlsService()

        @require_permission("suggest")
        async def make_suggestion(agent_id: uuid.UUID):
            return {"suggestion": "Decorated suggestion"}

        # The decorated function should check permissions
        result = await make_suggestion(uuid.UUID(agent["id"]))

        assert result["suggestion"] == "Decorated suggestion"

    @pytest.mark.asyncio
    async def test_scenario_decorated_function_blocked_on_permission_denied(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Decorated function raises error when permission denied
        Given a function decorated with @require_permission("act")
        And my autonomy mode is "suggest"
        When the function is called
        Then a PermissionDeniedError is raised
        """
        from app.services.autonomy_controls_service import (
            AutonomyControlsService,
            require_permission,
            PermissionDeniedError
        )

        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        @require_permission("act")
        async def take_action(agent_id: uuid.UUID):
            return {"action": "Should not reach here"}

        with pytest.raises(PermissionDeniedError) as exc_info:
            await take_action(uuid.UUID(agent["id"]))

        assert "not allowed" in str(exc_info.value).lower()
