"""
Unit Tests for Advisor Agent Service
Tests advisor agent operations using ZeroDB NoSQL + Vectors
"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.advisor_agent import AgentStatus, MemoryType
from app.schemas.advisor_agent import AgentMemoryCreate, AdvisorAgentUpdate
from app.services.advisor_agent_service import AdvisorAgentService
from app.core.enums import AutonomyMode


class TestAdvisorAgentInitialization:
    """Tests for agent initialization"""

    @pytest.mark.asyncio
    async def test_initialize_agent_success(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test successful agent initialization for a user"""
        user, profile, _ = sample_user_with_profile_and_agent_dict

        # Configure mocks - user exists, no existing agent
        mock_zerodb_client.get_by_id.return_value = user
        mock_zerodb_client.query_rows.return_value = []  # No existing agent

        service = AdvisorAgentService()
        agent = await service.initialize_agent(uuid.UUID(user["id"]))

        assert agent["user_id"] == user["id"]
        assert agent["status"] == AgentStatus.INITIALIZING.value
        assert agent["memory_namespace"] == f"agent_{user['id']}"
        assert agent["is_enabled"] is True
        mock_zerodb_client.insert_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_agent_user_not_found(self, mock_zerodb_client):
        """Test initialization fails when user not found"""
        mock_zerodb_client.get_by_id.return_value = None

        service = AdvisorAgentService()

        with pytest.raises(ValueError, match="User not found"):
            await service.initialize_agent(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_initialize_agent_already_exists(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test initialization fails when agent already exists"""
        user, profile, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = user
        mock_zerodb_client.query_rows.return_value = [agent]  # Existing agent

        service = AdvisorAgentService()

        with pytest.raises(ValueError, match="already has an advisor agent"):
            await service.initialize_agent(uuid.UUID(user["id"]))


class TestAgentRetrieval:
    """Tests for agent retrieval operations"""

    @pytest.mark.asyncio
    async def test_get_agent_by_id(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test retrieving agent by ID"""
        _, _, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()
        result = await service.get_agent(uuid.UUID(agent["id"]))

        assert result == agent
        mock_zerodb_client.get_by_id.assert_called_with("advisor_agents", agent["id"])

    @pytest.mark.asyncio
    async def test_get_agent_by_user_id(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test retrieving agent by user ID"""
        user, _, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.query_rows.return_value = [agent]

        service = AdvisorAgentService()
        result = await service.get_agent_by_user_id(uuid.UUID(user["id"]))

        assert result == agent

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, mock_zerodb_client):
        """Test get_agent returns None when not found"""
        mock_zerodb_client.get_by_id.return_value = None

        service = AdvisorAgentService()
        result = await service.get_agent(uuid.uuid4())

        assert result is None


class TestAgentLifecycle:
    """Tests for agent activation/deactivation"""

    @pytest.mark.asyncio
    async def test_activate_agent(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test activating an agent"""
        _, _, agent = sample_user_with_profile_and_agent_dict
        agent["status"] = AgentStatus.INITIALIZING.value

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()
        result = await service.activate_agent(uuid.UUID(agent["id"]))

        assert result["status"] == AgentStatus.ACTIVE.value
        mock_zerodb_client.update_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_agent(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test deactivating an agent"""
        _, _, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()
        result = await service.deactivate_agent(uuid.UUID(agent["id"]))

        assert result["status"] == AgentStatus.DEACTIVATED.value
        mock_zerodb_client.update_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_agent_not_found(self, mock_zerodb_client):
        """Test activating non-existent agent raises error"""
        mock_zerodb_client.get_by_id.return_value = None

        service = AdvisorAgentService()

        with pytest.raises(ValueError, match="Agent not found"):
            await service.activate_agent(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_update_agent(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test updating agent settings"""
        _, _, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()
        update_data = AdvisorAgentUpdate(name="Updated Name", is_enabled=False)
        result = await service.update_agent(uuid.UUID(agent["id"]), update_data)

        assert result["name"] == "Updated Name"
        assert result["is_enabled"] is False
        mock_zerodb_client.update_rows.assert_called_once()


class TestPermissionChecks:
    """Tests for permission checking based on autonomy mode"""

    @pytest.mark.asyncio
    async def test_suggest_permission_in_suggest_mode(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test suggestions are allowed in suggest mode"""
        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AdvisorAgentService()
        allowed, reason = await service.check_permission(uuid.UUID(agent["id"]), "suggest")

        assert allowed is True
        assert "allowed" in reason.lower()

    @pytest.mark.asyncio
    async def test_act_permission_denied_in_suggest_mode(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test autonomous actions are denied in suggest mode"""
        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AdvisorAgentService()
        allowed, reason = await service.check_permission(uuid.UUID(agent["id"]), "act")

        assert allowed is False
        assert "not allowed" in reason.lower()

    @pytest.mark.asyncio
    async def test_act_permission_in_auto_mode(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test autonomous actions are allowed in auto mode"""
        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.AUTO.value

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AdvisorAgentService()
        allowed, reason = await service.check_permission(uuid.UUID(agent["id"]), "act")

        assert allowed is True
        assert "allowed" in reason.lower()

    @pytest.mark.asyncio
    async def test_permission_denied_when_agent_disabled(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test permissions denied when agent is disabled"""
        user, profile, agent = sample_user_with_profile_and_agent_dict
        agent["is_enabled"] = False

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()
        allowed, reason = await service.check_permission(uuid.UUID(agent["id"]), "suggest")

        assert allowed is False
        assert "disabled" in reason.lower()

    @pytest.mark.asyncio
    async def test_permission_denied_when_agent_paused(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test permissions denied when agent is paused"""
        user, profile, agent = sample_user_with_profile_and_agent_dict
        agent["status"] = AgentStatus.PAUSED.value

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()
        allowed, reason = await service.check_permission(uuid.UUID(agent["id"]), "act")

        assert allowed is False
        assert "not active" in reason.lower()


class TestMemoryOperations:
    """Tests for agent memory storage and retrieval"""

    @pytest.mark.asyncio
    async def test_store_memory_success(
        self,
        mock_zerodb_client,
        mock_zerodb_vector_service,
        mock_embedding_service,
        sample_user_with_profile_and_agent_dict
    ):
        """Test storing a memory with embedding"""
        user, profile, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()
        memory_data = AgentMemoryCreate(
            memory_type=MemoryType.PREFERENCE,
            content="User prefers morning meetings",
            summary="Morning preference",
            confidence=85
        )

        memory = await service.store_memory(uuid.UUID(agent["id"]), memory_data)

        assert memory["memory_type"] == MemoryType.PREFERENCE.value
        assert memory["content"] == "User prefers morning meetings"
        assert memory["embedding_id"] == "vec_test_123"
        mock_zerodb_client.insert_rows.assert_called_once()
        mock_zerodb_client.update_rows.assert_called_once()  # Update agent stats

    @pytest.mark.asyncio
    async def test_store_memory_agent_not_found(self, mock_zerodb_client):
        """Test storing memory fails when agent not found"""
        mock_zerodb_client.get_by_id.return_value = None

        service = AdvisorAgentService()
        memory_data = AgentMemoryCreate(
            memory_type=MemoryType.PREFERENCE,
            content="Test content",
            confidence=80
        )

        with pytest.raises(ValueError, match="Agent not found"):
            await service.store_memory(uuid.uuid4(), memory_data)

    @pytest.mark.asyncio
    async def test_get_memories(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test retrieving agent memories"""
        _, _, agent = sample_user_with_profile_and_agent_dict
        memories = [
            {"id": str(uuid.uuid4()), "memory_type": "preference", "content": "Memory 1"},
            {"id": str(uuid.uuid4()), "memory_type": "preference", "content": "Memory 2"},
        ]

        mock_zerodb_client.query_rows.return_value = memories

        service = AdvisorAgentService()
        result = await service.get_memories(uuid.UUID(agent["id"]))

        assert len(result) == 2
        mock_zerodb_client.query_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_memories_filtered_by_type(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test retrieving memories filtered by type"""
        _, _, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.query_rows.return_value = []

        service = AdvisorAgentService()
        await service.get_memories(uuid.UUID(agent["id"]), memory_type=MemoryType.OUTCOME)

        call_args = mock_zerodb_client.query_rows.call_args
        assert call_args.kwargs["filter"]["memory_type"] == MemoryType.OUTCOME.value


class TestWeeklySummary:
    """Tests for weekly summary generation"""

    @pytest.mark.asyncio
    async def test_generate_weekly_summary(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test generating weekly summary"""
        _, _, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = []  # No recent memories

        service = AdvisorAgentService()
        summary = await service.generate_weekly_summary(uuid.UUID(agent["id"]))

        assert summary.period_start is not None
        assert summary.period_end is not None
        assert (summary.period_end - summary.period_start).days == 7
        assert "memories_analyzed" in summary.metrics
        mock_zerodb_client.update_rows.assert_called_once()  # Update last_summary_at

    @pytest.mark.asyncio
    async def test_generate_weekly_summary_agent_not_found(self, mock_zerodb_client):
        """Test summary generation fails when agent not found"""
        mock_zerodb_client.get_by_id.return_value = None

        service = AdvisorAgentService()

        with pytest.raises(ValueError, match="Agent not found"):
            await service.generate_weekly_summary(uuid.uuid4())


class TestOutcomeLearning:
    """Tests for learning from outcomes"""

    @pytest.mark.asyncio
    async def test_learn_from_successful_outcome(
        self,
        mock_zerodb_client,
        mock_zerodb_vector_service,
        mock_embedding_service,
        sample_user_with_profile_and_agent_dict
    ):
        """Test learning from a successful outcome"""
        _, _, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()
        memory = await service.learn_from_outcome(
            agent_id=uuid.UUID(agent["id"]),
            outcome_type="introduction",
            success=True,
            context={"partner": "Tech CEO"}
        )

        assert memory["memory_type"] == MemoryType.OUTCOME.value
        assert "Success" in memory["content"]
        assert memory["confidence"] == 80  # Higher for success

    @pytest.mark.asyncio
    async def test_learn_from_failed_outcome(
        self,
        mock_zerodb_client,
        mock_zerodb_vector_service,
        mock_embedding_service,
        sample_user_with_profile_and_agent_dict
    ):
        """Test learning from a failed outcome"""
        _, _, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()
        memory = await service.learn_from_outcome(
            agent_id=uuid.UUID(agent["id"]),
            outcome_type="introduction",
            success=False,
            context={"reason": "timing_mismatch"}
        )

        assert memory["memory_type"] == MemoryType.OUTCOME.value
        assert "Failure" in memory["content"]
        assert memory["confidence"] == 60  # Lower for failure


class TestActivityTracking:
    """Tests for recording agent activity"""

    @pytest.mark.asyncio
    async def test_record_suggestion(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test recording a suggestion"""
        _, _, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()
        await service.record_suggestion(uuid.UUID(agent["id"]))

        mock_zerodb_client.update_rows.assert_called_once()
        update_call = mock_zerodb_client.update_rows.call_args
        assert update_call.kwargs["update"]["$set"]["total_suggestions"] == 1

    @pytest.mark.asyncio
    async def test_record_action(
        self,
        mock_zerodb_client,
        sample_user_with_profile_and_agent_dict
    ):
        """Test recording an action"""
        _, _, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()
        await service.record_action(uuid.UUID(agent["id"]))

        mock_zerodb_client.update_rows.assert_called_once()
        update_call = mock_zerodb_client.update_rows.call_args
        assert update_call.kwargs["update"]["$set"]["total_actions"] == 1
