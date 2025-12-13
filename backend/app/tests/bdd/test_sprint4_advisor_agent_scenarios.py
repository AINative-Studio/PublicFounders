"""
BDD Scenarios for Sprint 4: Virtual Advisor Agent
Behavior-Driven Development tests for advisor agent initialization and weekly summaries
Uses ZeroDB NoSQL + Vectors (not PostgreSQL)
"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, AsyncMock

from app.models.advisor_agent import AgentStatus, MemoryType
from app.services.advisor_agent_service import AdvisorAgentService
from app.schemas.advisor_agent import AgentMemoryCreate
from app.core.enums import AutonomyMode


@pytest.mark.bdd
class TestStory6_1_InitializeAdvisorAgent:
    """
    Story 6.1: Initialize Advisor Agent
    As a founder, I want an AI advisor agent that learns from my interactions
    So that it can provide personalized suggestions over time
    """

    @pytest.mark.asyncio
    async def test_scenario_agent_created_with_isolated_memory(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Agent has isolated memory namespace
        Given I have a founder profile
        When my advisor agent is initialized
        Then it has a unique memory namespace scoped to my user ID
        """
        # Given: I have a founder profile
        user, profile, _ = sample_user_with_profile_and_agent_dict

        # Configure mock
        mock_zerodb_client.get_by_id.return_value = user
        mock_zerodb_client.query_rows.return_value = []  # No existing agent

        service = AdvisorAgentService()

        # When: My advisor agent is initialized
        agent = await service.initialize_agent(uuid.UUID(user["id"]))

        # Then: It has a unique memory namespace scoped to my user ID
        assert agent["memory_namespace"] == f"agent_{user['id']}"
        assert agent["memory_namespace"] != f"agent_{str(uuid.uuid4())}"

    @pytest.mark.asyncio
    async def test_scenario_agent_respects_autonomy_mode_suggest(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Agent respects suggest autonomy mode
        Given my autonomy mode is "suggest"
        When the agent wants to make a suggestion
        Then it is allowed to suggest
        And it is NOT allowed to act autonomously
        """
        # Given: My autonomy mode is "suggest"
        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.SUGGEST.value

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AdvisorAgentService()

        # When: The agent wants to make a suggestion
        suggest_allowed, suggest_reason = await service.check_permission(
            uuid.UUID(agent["id"]), "suggest"
        )

        # Then: It is allowed to suggest
        assert suggest_allowed is True

        # When: The agent wants to act autonomously
        act_allowed, act_reason = await service.check_permission(
            uuid.UUID(agent["id"]), "act"
        )

        # Then: It is NOT allowed to act autonomously
        assert act_allowed is False

    @pytest.mark.asyncio
    async def test_scenario_agent_respects_autonomy_mode_approve(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Agent respects approve autonomy mode
        Given my autonomy mode is "approve"
        When the agent wants to act
        Then it must wait for my approval
        """
        # Given: My autonomy mode is "approve"
        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.APPROVE.value

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AdvisorAgentService()

        # When: The agent wants to act
        act_allowed, act_reason = await service.check_permission(
            uuid.UUID(agent["id"]), "act"
        )

        # Then: It must wait for approval (not allowed to act autonomously)
        assert act_allowed is False
        assert "not allowed" in act_reason.lower()

    @pytest.mark.asyncio
    async def test_scenario_agent_can_act_in_auto_mode(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Agent can act autonomously in auto mode
        Given my autonomy mode is "auto"
        When the agent wants to act
        Then it can proceed without my approval
        """
        # Given: My autonomy mode is "auto"
        user, profile, agent = sample_user_with_profile_and_agent_dict
        profile["autonomy_mode"] = AutonomyMode.AUTO.value

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = [profile]

        service = AdvisorAgentService()

        # When: The agent wants to act
        act_allowed, act_reason = await service.check_permission(
            uuid.UUID(agent["id"]), "act"
        )

        # Then: It can proceed without my approval
        assert act_allowed is True
        assert "allowed" in act_reason.lower()

    @pytest.mark.asyncio
    async def test_scenario_agent_stores_memory_with_embedding(
        self,
        mock_zerodb_client,
        mock_zerodb_vector_service,
        mock_embedding_service,
        sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Agent stores memory with vector embedding
        Given my agent is active
        When it learns something about my preferences
        Then it stores the memory with a semantic embedding
        """
        # Given: My agent is active
        user, profile, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()

        # When: It learns something about my preferences
        memory_data = AgentMemoryCreate(
            memory_type=MemoryType.PREFERENCE,
            content="User prefers introductions in the morning",
            summary="Morning intro preference",
            confidence=85
        )

        memory = await service.store_memory(uuid.UUID(agent["id"]), memory_data)

        # Then: It stores the memory with a semantic embedding
        assert memory is not None
        assert memory["embedding_id"] == "vec_test_123"
        assert memory["memory_type"] == MemoryType.PREFERENCE.value
        mock_embedding_service.generate_embedding.assert_called_once()
        mock_zerodb_vector_service.upsert_vector.assert_called_once()


@pytest.mark.bdd
class TestStory6_2_WeeklyOpportunitySummary:
    """
    Story 6.2: Weekly Opportunity Summary
    As a founder, I want weekly summaries of networking opportunities
    So that I can review and act on potential connections
    """

    @pytest.mark.asyncio
    async def test_scenario_summary_is_reproducible(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Summary is reproducible
        Given I request a weekly summary
        When the summary is generated
        Then it includes a defined time period
        And it is based on my agent's memories
        """
        # Given: I request a weekly summary
        user, profile, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = []  # No recent memories

        service = AdvisorAgentService()

        # When: The summary is generated
        summary = await service.generate_weekly_summary(uuid.UUID(agent["id"]))

        # Then: It includes a defined time period
        assert summary.period_start is not None
        assert summary.period_end is not None
        assert summary.period_end > summary.period_start

        # And: The period is 7 days
        period_days = (summary.period_end - summary.period_start).days
        assert period_days == 7

        # And: It is based on my agent's memories (metrics tracked)
        assert "memories_analyzed" in summary.metrics

    @pytest.mark.asyncio
    async def test_scenario_summary_updates_agent_timestamp(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Summary generation updates timestamp
        Given I have an active agent
        When I request a weekly summary
        Then the agent's last_summary_at is updated
        """
        # Given: I have an active agent
        user, profile, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = agent
        mock_zerodb_client.query_rows.return_value = []

        service = AdvisorAgentService()

        # When: I request a weekly summary
        await service.generate_weekly_summary(uuid.UUID(agent["id"]))

        # Then: The agent's last_summary_at is updated (via update_rows call)
        mock_zerodb_client.update_rows.assert_called()
        update_call = mock_zerodb_client.update_rows.call_args
        assert "last_summary_at" in update_call.kwargs["update"]["$set"]


@pytest.mark.bdd
class TestAgentLearningFromOutcomes:
    """
    BDD scenarios for agent learning from interaction outcomes
    """

    @pytest.mark.asyncio
    async def test_scenario_agent_learns_from_successful_intro(
        self,
        mock_zerodb_client,
        mock_zerodb_vector_service,
        mock_embedding_service,
        sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Agent learns from successful introduction
        Given an introduction I made was successful
        When the outcome is recorded
        Then my agent stores a positive outcome memory
        """
        # Given: An introduction I made was successful
        user, profile, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()

        # When: The outcome is recorded
        memory = await service.learn_from_outcome(
            uuid.UUID(agent["id"]),
            outcome_type="introduction",
            success=True,
            context={"partner_industry": "fintech", "meeting_scheduled": True}
        )

        # Then: My agent stores a positive outcome memory
        assert memory is not None
        assert memory["memory_type"] == MemoryType.OUTCOME.value
        assert "Success" in memory["content"]
        assert memory["confidence"] == 80  # Higher confidence for success

    @pytest.mark.asyncio
    async def test_scenario_agent_learns_from_failed_intro(
        self,
        mock_zerodb_client,
        mock_zerodb_vector_service,
        mock_embedding_service,
        sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Agent learns from failed introduction
        Given an introduction I made was not successful
        When the outcome is recorded
        Then my agent stores a learning memory with lower confidence
        """
        # Given: An introduction I made was not successful
        user, profile, agent = sample_user_with_profile_and_agent_dict

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()

        # When: The outcome is recorded
        memory = await service.learn_from_outcome(
            uuid.UUID(agent["id"]),
            outcome_type="introduction",
            success=False,
            context={"reason": "timing_mismatch", "partner_busy": True}
        )

        # Then: My agent stores a learning memory with lower confidence
        assert memory is not None
        assert memory["memory_type"] == MemoryType.OUTCOME.value
        assert "Failure" in memory["content"]
        assert memory["confidence"] == 60  # Lower confidence for failure


@pytest.mark.bdd
class TestAgentDisabledBehavior:
    """
    BDD scenarios for agent behavior when disabled
    """

    @pytest.mark.asyncio
    async def test_scenario_disabled_agent_cannot_suggest(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Disabled agent cannot make suggestions
        Given I have disabled my advisor agent
        When it tries to make a suggestion
        Then the suggestion is blocked
        """
        # Given: I have disabled my advisor agent
        user, profile, agent = sample_user_with_profile_and_agent_dict
        agent["is_enabled"] = False

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()

        # When: It tries to make a suggestion
        allowed, reason = await service.check_permission(
            uuid.UUID(agent["id"]), "suggest"
        )

        # Then: The suggestion is blocked
        assert allowed is False
        assert "disabled" in reason.lower()

    @pytest.mark.asyncio
    async def test_scenario_paused_agent_cannot_act(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Paused agent cannot take actions
        Given my agent is paused
        When it tries to take an action
        Then the action is blocked
        """
        # Given: My agent is paused
        user, profile, agent = sample_user_with_profile_and_agent_dict
        agent["status"] = AgentStatus.PAUSED.value

        mock_zerodb_client.get_by_id.return_value = agent

        service = AdvisorAgentService()

        # When: It tries to take an action
        allowed, reason = await service.check_permission(
            uuid.UUID(agent["id"]), "act"
        )

        # Then: The action is blocked
        assert allowed is False
        assert "not active" in reason.lower()


@pytest.mark.bdd
class TestAgentMemoryIsolation:
    """
    BDD scenarios for agent memory isolation between users
    """

    @pytest.mark.asyncio
    async def test_scenario_agents_have_separate_namespaces(
        self, mock_zerodb_client, sample_user_with_profile_and_agent_dict
    ):
        """
        Scenario: Different users have isolated agent memories
        Given two founders with agents
        When they initialize agents
        Then their agents have separate namespaces
        """
        # Given: Two founders with agents
        user1, profile1, _ = sample_user_with_profile_and_agent_dict

        # Create second user dict
        user2_id = str(uuid.uuid4())
        user2 = {
            "id": user2_id,
            "linkedin_id": "linkedin_user2_isolation",
            "name": "Second User",
            "email": "user2@example.com",
            "is_active": True
        }

        service = AdvisorAgentService()

        # Mock for first user - user exists, no agent
        mock_zerodb_client.get_by_id.return_value = user1
        mock_zerodb_client.query_rows.return_value = []

        agent1 = await service.initialize_agent(uuid.UUID(user1["id"]))

        # Mock for second user
        mock_zerodb_client.get_by_id.return_value = user2
        mock_zerodb_client.query_rows.return_value = []

        agent2 = await service.initialize_agent(uuid.UUID(user2_id))

        # Then: Their memories are in separate namespaces
        assert agent1["memory_namespace"] != agent2["memory_namespace"]
        assert user1["id"] in agent1["memory_namespace"]
        assert user2_id in agent2["memory_namespace"]
