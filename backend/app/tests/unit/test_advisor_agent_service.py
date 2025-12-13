"""
Unit Tests for Advisor Agent Service
TDD tests for advisor agent initialization, memory, and permissions
"""
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.advisor_agent_service import AdvisorAgentService
from app.models.user import User
from app.models.founder_profile import FounderProfile, AutonomyMode
from app.models.advisor_agent import AdvisorAgent, AgentMemory, AgentStatus, MemoryType
from app.schemas.advisor_agent import AgentMemoryCreate, AdvisorAgentUpdate


@pytest.fixture
async def sample_user_with_profile_and_agent(db_session: AsyncSession) -> tuple[User, FounderProfile, AdvisorAgent]:
    """Create a sample user with founder profile and advisor agent"""
    user = User(
        id=uuid.uuid4(),
        linkedin_id="linkedin_agent_test",
        name="Agent Test User",
        headline="Founder Testing Agent",
        email="agent.test@example.com",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db_session.add(user)
    await db_session.flush()

    profile = FounderProfile(
        user_id=user.id,
        bio="Testing advisor agent functionality",
        current_focus="Building AI-powered features",
        autonomy_mode=AutonomyMode.SUGGEST,
        public_visibility=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db_session.add(profile)
    await db_session.flush()

    agent = AdvisorAgent(
        id=uuid.uuid4(),
        user_id=user.id,
        status=AgentStatus.ACTIVE,
        name="Test Advisor",
        memory_namespace=f"agent_{str(user.id)}",
        total_memories=0,
        total_suggestions=0,
        total_actions=0,
        is_enabled=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(profile)
    await db_session.refresh(agent)

    return user, profile, agent


@pytest.mark.unit
class TestAgentInitialization:
    """Test suite for agent initialization"""

    @pytest.mark.asyncio
    async def test_initialize_agent_creates_new_agent(self, db_session: AsyncSession, sample_user_with_profile):
        """Test initializing a new advisor agent for a user"""
        # Arrange
        user, profile = sample_user_with_profile
        service = AdvisorAgentService(db_session)

        # Act
        agent = await service.initialize_agent(user.id)
        await db_session.commit()

        # Assert
        assert agent is not None
        assert agent.user_id == user.id
        assert agent.status == AgentStatus.INITIALIZING
        assert agent.memory_namespace == f"agent_{str(user.id)}"
        assert agent.is_enabled is True
        assert agent.total_memories == 0

    @pytest.mark.asyncio
    async def test_initialize_agent_fails_for_nonexistent_user(self, db_session: AsyncSession):
        """Test initialization fails for non-existent user"""
        # Arrange
        service = AdvisorAgentService(db_session)
        nonexistent_user_id = uuid.uuid4()

        # Act & Assert
        with pytest.raises(ValueError, match="User not found"):
            await service.initialize_agent(nonexistent_user_id)

    @pytest.mark.asyncio
    async def test_initialize_agent_fails_if_agent_exists(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test initialization fails if user already has an agent"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        service = AdvisorAgentService(db_session)

        # Act & Assert
        with pytest.raises(ValueError, match="User already has an advisor agent"):
            await service.initialize_agent(user.id)

    @pytest.mark.asyncio
    async def test_get_agent_by_user_id(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test retrieving agent by user ID"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        service = AdvisorAgentService(db_session)

        # Act
        retrieved_agent = await service.get_agent_by_user_id(user.id)

        # Assert
        assert retrieved_agent is not None
        assert retrieved_agent.id == agent.id
        assert retrieved_agent.user_id == user.id

    @pytest.mark.asyncio
    async def test_get_agent_by_user_id_returns_none_for_nonexistent(self, db_session: AsyncSession):
        """Test retrieving agent for non-existent user returns None"""
        # Arrange
        service = AdvisorAgentService(db_session)
        nonexistent_user_id = uuid.uuid4()

        # Act
        agent = await service.get_agent_by_user_id(nonexistent_user_id)

        # Assert
        assert agent is None


@pytest.mark.unit
class TestAgentLifecycle:
    """Test suite for agent lifecycle management"""

    @pytest.mark.asyncio
    async def test_activate_agent(self, db_session: AsyncSession, sample_user_with_profile):
        """Test activating an agent"""
        # Arrange
        user, profile = sample_user_with_profile
        service = AdvisorAgentService(db_session)

        # Create agent in INITIALIZING status
        agent = await service.initialize_agent(user.id)
        await db_session.commit()

        # Act
        activated_agent = await service.activate_agent(agent.id)
        await db_session.commit()

        # Assert
        assert activated_agent.status == AgentStatus.ACTIVE
        assert activated_agent.last_active_at is not None

    @pytest.mark.asyncio
    async def test_deactivate_agent(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test deactivating an agent"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        service = AdvisorAgentService(db_session)

        # Act
        deactivated_agent = await service.deactivate_agent(agent.id)
        await db_session.commit()

        # Assert
        assert deactivated_agent.status == AgentStatus.DEACTIVATED

    @pytest.mark.asyncio
    async def test_update_agent_name(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test updating agent name"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        service = AdvisorAgentService(db_session)

        update_data = AdvisorAgentUpdate(name="Custom Advisor Name")

        # Act
        updated_agent = await service.update_agent(agent.id, update_data)
        await db_session.commit()

        # Assert
        assert updated_agent.name == "Custom Advisor Name"

    @pytest.mark.asyncio
    async def test_disable_agent(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test disabling an agent"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        service = AdvisorAgentService(db_session)

        update_data = AdvisorAgentUpdate(is_enabled=False)

        # Act
        updated_agent = await service.update_agent(agent.id, update_data)
        await db_session.commit()

        # Assert
        assert updated_agent.is_enabled is False


@pytest.mark.unit
class TestAgentPermissions:
    """Test suite for agent permission checks based on autonomy mode"""

    @pytest.mark.asyncio
    async def test_check_permission_suggest_in_suggest_mode(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test suggest permission in suggest autonomy mode"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        profile.autonomy_mode = AutonomyMode.SUGGEST
        await db_session.commit()

        service = AdvisorAgentService(db_session)

        # Act
        allowed, reason = await service.check_permission(agent.id, "suggest")

        # Assert
        assert allowed is True
        assert "allowed" in reason.lower()

    @pytest.mark.asyncio
    async def test_check_permission_act_in_suggest_mode_denied(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test autonomous action denied in suggest mode"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        profile.autonomy_mode = AutonomyMode.SUGGEST
        await db_session.commit()

        service = AdvisorAgentService(db_session)

        # Act
        allowed, reason = await service.check_permission(agent.id, "act")

        # Assert
        assert allowed is False
        assert "not allowed" in reason.lower()

    @pytest.mark.asyncio
    async def test_check_permission_act_in_auto_mode_allowed(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test autonomous action allowed in auto mode"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        profile.autonomy_mode = AutonomyMode.AUTO
        await db_session.commit()

        service = AdvisorAgentService(db_session)

        # Act
        allowed, reason = await service.check_permission(agent.id, "act")

        # Assert
        assert allowed is True
        assert "allowed" in reason.lower()

    @pytest.mark.asyncio
    async def test_check_permission_denied_when_agent_disabled(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test permission denied when agent is disabled"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        agent.is_enabled = False
        await db_session.commit()

        service = AdvisorAgentService(db_session)

        # Act
        allowed, reason = await service.check_permission(agent.id, "suggest")

        # Assert
        assert allowed is False
        assert "disabled" in reason.lower()

    @pytest.mark.asyncio
    async def test_check_permission_denied_when_agent_not_active(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test permission denied when agent is not active"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        agent.status = AgentStatus.PAUSED
        await db_session.commit()

        service = AdvisorAgentService(db_session)

        # Act
        allowed, reason = await service.check_permission(agent.id, "suggest")

        # Assert
        assert allowed is False
        assert "not active" in reason.lower()


@pytest.mark.unit
class TestAgentMemory:
    """Test suite for agent memory storage and retrieval"""

    @pytest.mark.asyncio
    async def test_store_memory_creates_record(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test storing a memory creates a record"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        service = AdvisorAgentService(db_session)

        memory_data = AgentMemoryCreate(
            memory_type=MemoryType.PREFERENCE,
            content="User prefers morning introductions",
            summary="Morning intro preference",
            confidence=90
        )

        # Mock embedding service
        with patch.object(service.embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 1536

            with patch.object(service.zerodb, 'upsert_vector', new_callable=AsyncMock) as mock_upsert:
                mock_upsert.return_value = "vec_123"

                # Act
                memory = await service.store_memory(agent.id, memory_data)
                await db_session.commit()

        # Assert
        assert memory is not None
        assert memory.agent_id == agent.id
        assert memory.memory_type == MemoryType.PREFERENCE
        assert memory.content == "User prefers morning introductions"
        assert memory.confidence == 90

    @pytest.mark.asyncio
    async def test_store_memory_updates_agent_stats(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test storing memory updates agent stats"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        original_total = agent.total_memories
        service = AdvisorAgentService(db_session)

        memory_data = AgentMemoryCreate(
            memory_type=MemoryType.OUTCOME,
            content="Introduction was successful",
            confidence=85
        )

        # Mock services
        with patch.object(service.embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 1536

            with patch.object(service.zerodb, 'upsert_vector', new_callable=AsyncMock) as mock_upsert:
                mock_upsert.return_value = "vec_456"

                # Act
                await service.store_memory(agent.id, memory_data)
                await db_session.commit()
                await db_session.refresh(agent)

        # Assert
        assert agent.total_memories == original_total + 1
        assert agent.last_memory_at is not None

    @pytest.mark.asyncio
    async def test_get_memories_returns_agent_memories(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test retrieving memories for an agent"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent

        # Create a memory directly
        memory = AgentMemory(
            agent_id=agent.id,
            memory_type=MemoryType.CONTEXT,
            content="Working on fundraising",
            confidence=75,
            created_at=datetime.utcnow()
        )
        db_session.add(memory)
        await db_session.commit()

        service = AdvisorAgentService(db_session)

        # Act
        memories = await service.get_memories(agent.id)

        # Assert
        assert len(memories) >= 1
        assert any(m.content == "Working on fundraising" for m in memories)

    @pytest.mark.asyncio
    async def test_get_memories_filters_by_type(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test retrieving memories filtered by type"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent

        # Create memories of different types
        mem1 = AgentMemory(
            agent_id=agent.id,
            memory_type=MemoryType.PREFERENCE,
            content="Prefers email",
            confidence=80,
            created_at=datetime.utcnow()
        )
        mem2 = AgentMemory(
            agent_id=agent.id,
            memory_type=MemoryType.OUTCOME,
            content="Meeting went well",
            confidence=90,
            created_at=datetime.utcnow()
        )
        db_session.add_all([mem1, mem2])
        await db_session.commit()

        service = AdvisorAgentService(db_session)

        # Act
        preference_memories = await service.get_memories(agent.id, memory_type=MemoryType.PREFERENCE)

        # Assert
        assert all(m.memory_type == MemoryType.PREFERENCE for m in preference_memories)


@pytest.mark.unit
class TestWeeklySummary:
    """Test suite for weekly opportunity summary generation"""

    @pytest.mark.asyncio
    async def test_generate_weekly_summary(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test generating weekly summary"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        service = AdvisorAgentService(db_session)

        # Act
        summary = await service.generate_weekly_summary(agent.id)
        await db_session.commit()

        # Assert
        assert summary is not None
        assert summary.generated_at is not None
        assert summary.period_start < summary.period_end
        assert (summary.period_end - summary.period_start).days == 7

    @pytest.mark.asyncio
    async def test_generate_summary_updates_last_summary_at(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test summary generation updates agent timestamp"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        original_summary_at = agent.last_summary_at
        service = AdvisorAgentService(db_session)

        # Act
        await service.generate_weekly_summary(agent.id)
        await db_session.commit()
        await db_session.refresh(agent)

        # Assert
        assert agent.last_summary_at is not None
        if original_summary_at:
            assert agent.last_summary_at > original_summary_at

    @pytest.mark.asyncio
    async def test_generate_summary_fails_for_nonexistent_agent(self, db_session: AsyncSession):
        """Test summary generation fails for non-existent agent"""
        # Arrange
        service = AdvisorAgentService(db_session)
        nonexistent_agent_id = uuid.uuid4()

        # Act & Assert
        with pytest.raises(ValueError, match="Agent not found"):
            await service.generate_weekly_summary(nonexistent_agent_id)


@pytest.mark.unit
class TestAgentLearning:
    """Test suite for agent learning from outcomes"""

    @pytest.mark.asyncio
    async def test_learn_from_positive_outcome(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test agent learning from positive outcome"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        service = AdvisorAgentService(db_session)

        # Mock services
        with patch.object(service.embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 1536

            with patch.object(service.zerodb, 'upsert_vector', new_callable=AsyncMock) as mock_upsert:
                mock_upsert.return_value = "vec_learn_123"

                # Act
                memory = await service.learn_from_outcome(
                    agent.id,
                    outcome_type="introduction",
                    success=True,
                    context={"target_industry": "fintech"}
                )
                await db_session.commit()

        # Assert
        assert memory is not None
        assert memory.memory_type == MemoryType.OUTCOME
        assert "Success" in memory.content
        assert memory.confidence == 80  # Higher confidence for success

    @pytest.mark.asyncio
    async def test_learn_from_negative_outcome(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test agent learning from negative outcome"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        service = AdvisorAgentService(db_session)

        # Mock services
        with patch.object(service.embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 1536

            with patch.object(service.zerodb, 'upsert_vector', new_callable=AsyncMock) as mock_upsert:
                mock_upsert.return_value = "vec_learn_456"

                # Act
                memory = await service.learn_from_outcome(
                    agent.id,
                    outcome_type="introduction",
                    success=False,
                    context={"reason": "timing mismatch"}
                )
                await db_session.commit()

        # Assert
        assert memory is not None
        assert "Failure" in memory.content
        assert memory.confidence == 60  # Lower confidence for failure

    @pytest.mark.asyncio
    async def test_record_suggestion_increments_counter(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test recording suggestion increments counter"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        original_suggestions = agent.total_suggestions
        service = AdvisorAgentService(db_session)

        # Act
        await service.record_suggestion(agent.id)
        await db_session.commit()
        await db_session.refresh(agent)

        # Assert
        assert agent.total_suggestions == original_suggestions + 1
        assert agent.last_active_at is not None

    @pytest.mark.asyncio
    async def test_record_action_increments_counter(
        self, db_session: AsyncSession, sample_user_with_profile_and_agent
    ):
        """Test recording action increments counter"""
        # Arrange
        user, profile, agent = sample_user_with_profile_and_agent
        original_actions = agent.total_actions
        service = AdvisorAgentService(db_session)

        # Act
        await service.record_action(agent.id)
        await db_session.commit()
        await db_session.refresh(agent)

        # Assert
        assert agent.total_actions == original_actions + 1
