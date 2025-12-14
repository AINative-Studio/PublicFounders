"""
Unit Tests for Autonomy Controls Service
Tests for Story 9.1: Agent actions always check autonomy mode
Uses ZeroDB NoSQL + Vectors (not PostgreSQL)
"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Callable

from app.models.advisor_agent import AgentStatus, MemoryType
from app.core.enums import AutonomyMode


class TestAutonomyControlsServiceInitialization:
    """Tests for AutonomyControlsService initialization"""

    @pytest.mark.asyncio
    async def test_service_initializes_with_zerodb_client(self, mock_zerodb_client):
        """Test service initializes with ZeroDB client dependency"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        service = AutonomyControlsService()

        assert service.zerodb_client is not None

    @pytest.mark.asyncio
    async def test_service_has_audit_logging_enabled(self, mock_zerodb_client):
        """Test service has audit logging enabled by default"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        service = AutonomyControlsService()

        assert service.audit_enabled is True


class TestPermissionChecking:
    """Tests for permission checking logic"""

    @pytest.mark.asyncio
    async def test_check_permission_returns_allowed_for_suggest_in_suggest_mode(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test suggestions are allowed in suggest mode"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AutonomyControlsService()
        allowed, reason = await service.check_permission(
            uuid.UUID(agent["id"]), "suggest"
        )

        assert allowed is True
        assert "allowed" in reason.lower()

    @pytest.mark.asyncio
    async def test_check_permission_returns_denied_for_act_in_suggest_mode(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test autonomous actions are denied in suggest mode"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AutonomyControlsService()
        allowed, reason = await service.check_permission(
            uuid.UUID(agent["id"]), "act"
        )

        assert allowed is False
        assert "not allowed" in reason.lower()

    @pytest.mark.asyncio
    async def test_check_permission_returns_allowed_for_act_in_auto_mode(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test autonomous actions are allowed in auto mode"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.AUTO.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AutonomyControlsService()
        allowed, reason = await service.check_permission(
            uuid.UUID(agent["id"]), "act"
        )

        assert allowed is True
        assert "allowed" in reason.lower()

    @pytest.mark.asyncio
    async def test_check_permission_denied_when_agent_not_found(
        self, mock_zerodb_client
    ):
        """Test permission denied when agent not found"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        mock_zerodb_client.get_by_id.return_value = None

        service = AutonomyControlsService()
        allowed, reason = await service.check_permission(uuid.uuid4(), "suggest")

        assert allowed is False
        assert "not found" in reason.lower()

    @pytest.mark.asyncio
    async def test_check_permission_denied_when_agent_disabled(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test permission denied when agent is disabled"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        agent["is_enabled"] = False

        mock_zerodb_client.get_by_id.return_value = agent

        service = AutonomyControlsService()
        allowed, reason = await service.check_permission(
            uuid.UUID(agent["id"]), "suggest"
        )

        assert allowed is False
        assert "disabled" in reason.lower()

    @pytest.mark.asyncio
    async def test_check_permission_denied_when_agent_not_active(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test permission denied when agent status is not active"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        agent["status"] = AgentStatus.PAUSED.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent

        service = AutonomyControlsService()
        allowed, reason = await service.check_permission(
            uuid.UUID(agent["id"]), "act"
        )

        assert allowed is False
        assert "not active" in reason.lower()

    @pytest.mark.asyncio
    async def test_check_permission_denied_when_profile_not_found(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test permission denied when founder profile not found"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = []  # No profile

        service = AutonomyControlsService()
        allowed, reason = await service.check_permission(
            uuid.UUID(agent["id"]), "suggest"
        )

        assert allowed is False
        assert "profile not found" in reason.lower()


class TestExecuteWithPermissionCheck:
    """Tests for execute_with_permission_check method"""

    @pytest.mark.asyncio
    async def test_execute_runs_action_when_permitted(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test action executes when permission is granted"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AutonomyControlsService()

        action_executed = False

        def test_action():
            nonlocal action_executed
            action_executed = True
            return {"result": "success"}

        result = await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_fn=test_action
        )

        assert action_executed is True
        assert result["success"] is True
        assert result["action_result"] == {"result": "success"}

    @pytest.mark.asyncio
    async def test_execute_blocks_action_when_denied(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test action is blocked when permission is denied"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AutonomyControlsService()

        action_executed = False

        def test_action():
            nonlocal action_executed
            action_executed = True
            return {"result": "should not reach"}

        result = await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="act",  # Not allowed in suggest mode
            action_fn=test_action
        )

        assert action_executed is False
        assert result["success"] is False
        assert result["blocked"] is True

    @pytest.mark.asyncio
    async def test_execute_marks_permission_checked(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test result includes permission_checked flag"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AutonomyControlsService()

        result = await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_fn=lambda: {}
        )

        assert result["permission_checked"] is True


class TestAuditLogging:
    """Tests for audit logging functionality"""

    @pytest.mark.asyncio
    async def test_permission_check_creates_audit_log(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test permission checks create audit log entries"""
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
            action_fn=lambda: {}
        )

        # Verify audit log insert was called
        insert_calls = mock_zerodb_client.insert_rows.call_args_list
        audit_calls = [c for c in insert_calls if c.args[0] == "autonomy_audit_log"]
        assert len(audit_calls) >= 1

    @pytest.mark.asyncio
    async def test_audit_log_contains_required_fields(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test audit log entries contain required fields"""
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
            action_fn=lambda: {}
        )

        insert_calls = mock_zerodb_client.insert_rows.call_args_list
        audit_calls = [c for c in insert_calls if c.args[0] == "autonomy_audit_log"]

        audit_entry = audit_calls[0].args[1][0]
        assert "id" in audit_entry
        assert "agent_id" in audit_entry
        assert "action_type" in audit_entry
        assert "allowed" in audit_entry
        assert "reason" in audit_entry
        assert "autonomy_mode" in audit_entry
        assert "timestamp" in audit_entry

    @pytest.mark.asyncio
    async def test_audit_log_disabled_when_configured(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test audit logging can be disabled"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AutonomyControlsService(audit_enabled=False)

        await service.execute_with_permission_check(
            agent_id=uuid.UUID(agent["id"]),
            action_type="suggest",
            action_fn=lambda: {}
        )

        # Verify no audit log was created
        insert_calls = mock_zerodb_client.insert_rows.call_args_list
        audit_calls = [c for c in insert_calls if c.args[0] == "autonomy_audit_log"]
        assert len(audit_calls) == 0


class TestPermissionDecoratorIntegration:
    """Tests for @require_permission decorator"""

    @pytest.mark.asyncio
    async def test_require_permission_decorator_allows_valid_action(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test decorator allows action when permission granted"""
        from app.services.autonomy_controls_service import require_permission

        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        @require_permission("suggest")
        async def make_suggestion(agent_id: uuid.UUID):
            return {"suggestion": "Test suggestion"}

        result = await make_suggestion(uuid.UUID(agent["id"]))

        assert result == {"suggestion": "Test suggestion"}

    @pytest.mark.asyncio
    async def test_require_permission_decorator_raises_on_denied(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test decorator raises PermissionDeniedError when denied"""
        from app.services.autonomy_controls_service import (
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
            return {"action": "Should not execute"}

        with pytest.raises(PermissionDeniedError):
            await take_action(uuid.UUID(agent["id"]))

    @pytest.mark.asyncio
    async def test_require_permission_decorator_logs_audit(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test decorator creates audit log entry"""
        import app.services.autonomy_controls_service as acs
        from app.services.autonomy_controls_service import (
            require_permission,
            get_autonomy_service
        )

        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value
        agent["status"] = AgentStatus.ACTIVE.value
        agent["is_enabled"] = True

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        # Reset and inject the mocked client into the global service
        acs._autonomy_service_instance = None
        service = get_autonomy_service()
        service.zerodb_client = mock_zerodb_client

        @require_permission("suggest")
        async def make_suggestion(agent_id: uuid.UUID):
            return {"suggestion": "Test"}

        await make_suggestion(uuid.UUID(agent["id"]))

        insert_calls = mock_zerodb_client.insert_rows.call_args_list
        audit_calls = [c for c in insert_calls if c.args[0] == "autonomy_audit_log"]
        assert len(audit_calls) >= 1


class TestGetAuditHistory:
    """Tests for retrieving audit history"""

    @pytest.mark.asyncio
    async def test_get_audit_history_by_agent(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test retrieving audit history for an agent"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict

        audit_entries = [
            {"id": str(uuid.uuid4()), "agent_id": agent["id"], "action_type": "suggest"},
            {"id": str(uuid.uuid4()), "agent_id": agent["id"], "action_type": "act"},
        ]
        mock_zerodb_client.query_rows.return_value = audit_entries

        service = AutonomyControlsService()
        history = await service.get_audit_history(uuid.UUID(agent["id"]))

        assert len(history) == 2
        mock_zerodb_client.query_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_audit_history_with_limit(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """Test retrieving limited audit history"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        user, profile, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.query_rows.return_value = []

        service = AutonomyControlsService()
        await service.get_audit_history(uuid.UUID(agent["id"]), limit=10)

        call_kwargs = mock_zerodb_client.query_rows.call_args.kwargs
        assert call_kwargs["limit"] == 10


class TestAutonomyModeDescriptions:
    """Tests for autonomy mode documentation/descriptions"""

    @pytest.mark.asyncio
    async def test_get_autonomy_mode_description_suggest(self, mock_zerodb_client):
        """Test getting description for suggest mode"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        service = AutonomyControlsService()
        desc = service.get_autonomy_mode_description(AutonomyMode.SUGGEST)

        assert "suggest" in desc.lower()
        assert len(desc) > 10

    @pytest.mark.asyncio
    async def test_get_autonomy_mode_description_approve(self, mock_zerodb_client):
        """Test getting description for approve mode"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        service = AutonomyControlsService()
        desc = service.get_autonomy_mode_description(AutonomyMode.APPROVE)

        assert "approve" in desc.lower() or "approval" in desc.lower()

    @pytest.mark.asyncio
    async def test_get_autonomy_mode_description_auto(self, mock_zerodb_client):
        """Test getting description for auto mode"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        service = AutonomyControlsService()
        desc = service.get_autonomy_mode_description(AutonomyMode.AUTO)

        assert "auto" in desc.lower() or "autonomous" in desc.lower()

    @pytest.mark.asyncio
    async def test_get_all_autonomy_modes(self, mock_zerodb_client):
        """Test getting all autonomy mode options"""
        from app.services.autonomy_controls_service import AutonomyControlsService

        service = AutonomyControlsService()
        modes = service.get_all_autonomy_modes()

        assert len(modes) == 3
        assert AutonomyMode.SUGGEST in modes
        assert AutonomyMode.APPROVE in modes
        assert AutonomyMode.AUTO in modes
