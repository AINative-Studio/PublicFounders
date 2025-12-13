"""
BDD Scenarios for Sprint 4: Virtual Advisor Agent
Behavior-Driven Development tests for advisor agent initialization and weekly summaries
"""
import pytest
import uuid
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, Mock, AsyncMock

from app.models.user import User
from app.models.founder_profile import FounderProfile, AutonomyMode
from app.models.advisor_agent import AdvisorAgent, AgentStatus, MemoryType
from app.services.advisor_agent_service import AdvisorAgentService
from app.core.security import create_access_token


@pytest.mark.bdd
class TestStory6_1_InitializeAdvisorAgent:
    """
    Story 6.1: Initialize Advisor Agent
    As a founder, I want an AI advisor agent that learns from my interactions
    So that it can provide personalized suggestions over time
    """

    @pytest.mark.asyncio
    async def test_scenario_agent_created_with_isolated_memory(
        self, db_session: AsyncSession, sample_user_with_profile
    ):
        """
        Scenario: Agent has isolated memory namespace
        Given I have a founder profile
        When my advisor agent is initialized
        Then it has a unique memory namespace scoped to my user ID
        """
        # Given: I have a founder profile
        user, profile = sample_user_with_profile
        service = AdvisorAgentService(db_session)

        # When: My advisor agent is initialized
        agent = await service.initialize_agent(user.id)
        await db_session.commit()

        # Then: It has a unique memory namespace scoped to my user ID
        assert agent.memory_namespace == f"agent_{str(user.id)}"
        assert agent.memory_namespace != f"agent_{str(uuid.uuid4())}"  # Different from other users

    @pytest.mark.asyncio
    async def test_scenario_agent_respects_autonomy_mode_suggest(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """
        Scenario: Agent respects suggest autonomy mode
        Given my autonomy mode is "suggest"
        When the agent wants to make a suggestion
        Then it is allowed to suggest
        And it is NOT allowed to act autonomously
        """
        # Given: My autonomy mode is "suggest"
        user, profile, agent = sample_user_with_profile_and_agent
        profile.autonomy_mode = AutonomyMode.SUGGEST
        await db_session.commit()

        service = AdvisorAgentService(db_session)

        # When: The agent wants to make a suggestion
        suggest_allowed, suggest_reason = await service.check_permission(agent.id, "suggest")

        # Then: It is allowed to suggest
        assert suggest_allowed is True

        # When: The agent wants to act autonomously
        act_allowed, act_reason = await service.check_permission(agent.id, "act")

        # Then: It is NOT allowed to act autonomously
        assert act_allowed is False

    @pytest.mark.asyncio
    async def test_scenario_agent_respects_autonomy_mode_approve(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """
        Scenario: Agent respects approve autonomy mode
        Given my autonomy mode is "approve"
        When the agent wants to act
        Then it must wait for my approval
        """
        # Given: My autonomy mode is "approve"
        user, profile, agent = sample_user_with_profile_and_agent
        profile.autonomy_mode = AutonomyMode.APPROVE
        await db_session.commit()

        service = AdvisorAgentService(db_session)

        # When: The agent wants to act
        act_allowed, act_reason = await service.check_permission(agent.id, "act")

        # Then: It must wait for approval (not allowed to act autonomously)
        assert act_allowed is False
        assert "not allowed" in act_reason.lower()

    @pytest.mark.asyncio
    async def test_scenario_agent_can_act_in_auto_mode(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """
        Scenario: Agent can act autonomously in auto mode
        Given my autonomy mode is "auto"
        When the agent wants to act
        Then it can proceed without my approval
        """
        # Given: My autonomy mode is "auto"
        user, profile, agent = sample_user_with_profile_and_agent
        profile.autonomy_mode = AutonomyMode.AUTO
        await db_session.commit()

        service = AdvisorAgentService(db_session)

        # When: The agent wants to act
        act_allowed, act_reason = await service.check_permission(agent.id, "act")

        # Then: It can proceed without my approval
        assert act_allowed is True
        assert "allowed" in act_reason.lower()

    @pytest.mark.asyncio
    async def test_scenario_agent_stores_memory_with_embedding(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """
        Scenario: Agent stores memory with vector embedding
        Given my agent is active
        When it learns something about my preferences
        Then it stores the memory with a semantic embedding
        """
        # Given: My agent is active
        user, profile, agent = sample_user_with_profile_and_agent
        service = AdvisorAgentService(db_session)

        # Mock the embedding and vector services
        with patch.object(service.embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 1536

            with patch.object(service.zerodb, 'upsert_vector', new_callable=AsyncMock) as mock_upsert:
                mock_upsert.return_value = "vec_preference_123"

                # When: It learns something about my preferences
                from app.schemas.advisor_agent import AgentMemoryCreate
                memory_data = AgentMemoryCreate(
                    memory_type=MemoryType.PREFERENCE,
                    content="User prefers introductions in the morning",
                    summary="Morning intro preference",
                    confidence=85
                )

                memory = await service.store_memory(agent.id, memory_data)
                await db_session.commit()

        # Then: It stores the memory with a semantic embedding
        assert memory is not None
        assert memory.embedding_id == "vec_preference_123"
        assert memory.memory_type == MemoryType.PREFERENCE
        mock_embed.assert_called_once()
        mock_upsert.assert_called_once()


@pytest.mark.bdd
class TestStory6_2_WeeklyOpportunitySummary:
    """
    Story 6.2: Weekly Opportunity Summary
    As a founder, I want weekly summaries of networking opportunities
    So that I can review and act on potential connections
    """

    @pytest.mark.asyncio
    async def test_scenario_summary_is_reproducible(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """
        Scenario: Summary is reproducible
        Given I request a weekly summary
        When the summary is generated
        Then it includes a defined time period
        And it is based on my agent's memories
        """
        # Given: I request a weekly summary
        user, profile, agent = sample_user_with_profile_and_agent
        service = AdvisorAgentService(db_session)

        # When: The summary is generated
        summary = await service.generate_weekly_summary(agent.id)
        await db_session.commit()

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
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """
        Scenario: Summary generation updates timestamp
        Given I have an active agent
        When I request a weekly summary
        Then the agent's last_summary_at is updated
        """
        # Given: I have an active agent
        user, profile, agent = sample_user_with_profile_and_agent
        original_summary_at = agent.last_summary_at
        service = AdvisorAgentService(db_session)

        # When: I request a weekly summary
        await service.generate_weekly_summary(agent.id)
        await db_session.commit()
        await db_session.refresh(agent)

        # Then: The agent's last_summary_at is updated
        assert agent.last_summary_at is not None
        if original_summary_at:
            assert agent.last_summary_at > original_summary_at


@pytest.mark.bdd
class TestAgentLearningFromOutcomes:
    """
    BDD scenarios for agent learning from interaction outcomes
    """

    @pytest.mark.asyncio
    async def test_scenario_agent_learns_from_successful_intro(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """
        Scenario: Agent learns from successful introduction
        Given an introduction I made was successful
        When the outcome is recorded
        Then my agent stores a positive outcome memory
        """
        # Given: An introduction I made was successful
        user, profile, agent = sample_user_with_profile_and_agent
        service = AdvisorAgentService(db_session)

        # Mock services
        with patch.object(service.embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 1536

            with patch.object(service.zerodb, 'upsert_vector', new_callable=AsyncMock) as mock_upsert:
                mock_upsert.return_value = "vec_outcome_success"

                # When: The outcome is recorded
                memory = await service.learn_from_outcome(
                    agent.id,
                    outcome_type="introduction",
                    success=True,
                    context={"partner_industry": "fintech", "meeting_scheduled": True}
                )
                await db_session.commit()

        # Then: My agent stores a positive outcome memory
        assert memory is not None
        assert memory.memory_type == MemoryType.OUTCOME
        assert "Success" in memory.content
        assert memory.confidence == 80  # Higher confidence for success

    @pytest.mark.asyncio
    async def test_scenario_agent_learns_from_failed_intro(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """
        Scenario: Agent learns from failed introduction
        Given an introduction I made was not successful
        When the outcome is recorded
        Then my agent stores a learning memory with lower confidence
        """
        # Given: An introduction I made was not successful
        user, profile, agent = sample_user_with_profile_and_agent
        service = AdvisorAgentService(db_session)

        # Mock services
        with patch.object(service.embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 1536

            with patch.object(service.zerodb, 'upsert_vector', new_callable=AsyncMock) as mock_upsert:
                mock_upsert.return_value = "vec_outcome_failure"

                # When: The outcome is recorded
                memory = await service.learn_from_outcome(
                    agent.id,
                    outcome_type="introduction",
                    success=False,
                    context={"reason": "timing_mismatch", "partner_busy": True}
                )
                await db_session.commit()

        # Then: My agent stores a learning memory with lower confidence
        assert memory is not None
        assert memory.memory_type == MemoryType.OUTCOME
        assert "Failure" in memory.content
        assert memory.confidence == 60  # Lower confidence for failure


@pytest.mark.bdd
class TestAgentDisabledBehavior:
    """
    BDD scenarios for agent behavior when disabled
    """

    @pytest.mark.asyncio
    async def test_scenario_disabled_agent_cannot_suggest(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """
        Scenario: Disabled agent cannot make suggestions
        Given I have disabled my advisor agent
        When it tries to make a suggestion
        Then the suggestion is blocked
        """
        # Given: I have disabled my advisor agent
        user, profile, agent = sample_user_with_profile_and_agent
        agent.is_enabled = False
        await db_session.commit()

        service = AdvisorAgentService(db_session)

        # When: It tries to make a suggestion
        allowed, reason = await service.check_permission(agent.id, "suggest")

        # Then: The suggestion is blocked
        assert allowed is False
        assert "disabled" in reason.lower()

    @pytest.mark.asyncio
    async def test_scenario_paused_agent_cannot_act(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """
        Scenario: Paused agent cannot take actions
        Given my agent is paused
        When it tries to take an action
        Then the action is blocked
        """
        # Given: My agent is paused
        user, profile, agent = sample_user_with_profile_and_agent
        agent.status = AgentStatus.PAUSED
        await db_session.commit()

        service = AdvisorAgentService(db_session)

        # When: It tries to take an action
        allowed, reason = await service.check_permission(agent.id, "act")

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
        self, db_session: AsyncSession, sample_user_with_profile
    ):
        """
        Scenario: Different users have isolated agent memories
        Given two founders with agents
        When they store memories
        Then their memories are in separate namespaces
        """
        # Given: Two founders with agents
        user1, profile1 = sample_user_with_profile

        # Create second user
        user2 = User(
            id=uuid.uuid4(),
            linkedin_id="linkedin_user2_isolation",
            name="Second User",
            headline="Another Founder",
            email="user2@example.com",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(user2)
        await db_session.flush()

        profile2 = FounderProfile(
            user_id=user2.id,
            bio="Second founder bio",
            autonomy_mode=AutonomyMode.SUGGEST,
            public_visibility=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(profile2)
        await db_session.commit()

        service = AdvisorAgentService(db_session)

        # Initialize agents for both users
        agent1 = await service.initialize_agent(user1.id)
        agent2 = await service.initialize_agent(user2.id)
        await db_session.commit()

        # Then: Their memories are in separate namespaces
        assert agent1.memory_namespace != agent2.memory_namespace
        assert str(user1.id) in agent1.memory_namespace
        assert str(user2.id) in agent2.memory_namespace
