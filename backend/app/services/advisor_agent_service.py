"""
Advisor Agent Service
Handles AI advisor agent lifecycle and operations for founders
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.founder_profile import FounderProfile
from app.models.advisor_agent import AdvisorAgent, AgentMemory, AgentStatus, MemoryType
from app.schemas.advisor_agent import (
    AgentMemoryCreate,
    AdvisorAgentUpdate,
    AgentSuggestion,
    WeeklyOpportunitySummary
)
from app.services.zerodb_service import zerodb_service
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class AdvisorAgentService:
    """
    Service for advisor agent management.

    Each founder has one advisor agent that:
    - Has isolated memory (scoped by agent_id in ZeroDB)
    - Cannot act without checking user's autonomy_mode permissions
    - Generates weekly opportunity summaries
    - Learns from interaction outcomes
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.zerodb = zerodb_service
        self.embedding_service = embedding_service

    async def initialize_agent(self, user_id: uuid.UUID) -> AdvisorAgent:
        """
        Initialize a new advisor agent for a user.

        This creates the agent in INITIALIZING status and sets up
        isolated memory namespace in ZeroDB.

        Args:
            user_id: User UUID

        Returns:
            Newly created AdvisorAgent

        Raises:
            ValueError: If user not found or already has an agent
        """
        # Verify user exists
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        # Check for existing agent
        existing = await self.get_agent_by_user_id(user_id)
        if existing:
            raise ValueError("User already has an advisor agent")

        # Create agent with isolated memory namespace
        agent = AdvisorAgent(
            user_id=user_id,
            status=AgentStatus.INITIALIZING,
            name="Advisor",
            memory_namespace=f"agent_{str(user_id)}",
            total_memories=0,
            total_suggestions=0,
            total_actions=0,
            is_enabled=True
        )

        self.db.add(agent)
        await self.db.flush()

        logger.info(f"Initialized advisor agent {agent.id} for user {user_id}")

        return agent

    async def get_agent_by_user_id(self, user_id: uuid.UUID) -> Optional[AdvisorAgent]:
        """
        Get advisor agent by user ID.

        Args:
            user_id: User UUID

        Returns:
            AdvisorAgent if found, None otherwise
        """
        stmt = select(AdvisorAgent).where(AdvisorAgent.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_agent(self, agent_id: uuid.UUID) -> Optional[AdvisorAgent]:
        """
        Get advisor agent by ID.

        Args:
            agent_id: Agent UUID

        Returns:
            AdvisorAgent if found, None otherwise
        """
        return await self.db.get(AdvisorAgent, agent_id)

    async def activate_agent(self, agent_id: uuid.UUID) -> AdvisorAgent:
        """
        Activate an advisor agent.

        Args:
            agent_id: Agent UUID

        Returns:
            Updated AdvisorAgent

        Raises:
            ValueError: If agent not found
        """
        agent = await self.db.get(AdvisorAgent, agent_id)
        if not agent:
            raise ValueError("Agent not found")

        agent.activate()
        await self.db.flush()

        logger.info(f"Activated advisor agent {agent_id}")
        return agent

    async def deactivate_agent(self, agent_id: uuid.UUID) -> AdvisorAgent:
        """
        Deactivate an advisor agent.

        Args:
            agent_id: Agent UUID

        Returns:
            Updated AdvisorAgent

        Raises:
            ValueError: If agent not found
        """
        agent = await self.db.get(AdvisorAgent, agent_id)
        if not agent:
            raise ValueError("Agent not found")

        agent.deactivate()
        await self.db.flush()

        logger.info(f"Deactivated advisor agent {agent_id}")
        return agent

    async def update_agent(
        self,
        agent_id: uuid.UUID,
        update_data: AdvisorAgentUpdate
    ) -> AdvisorAgent:
        """
        Update advisor agent settings.

        Args:
            agent_id: Agent UUID
            update_data: Update data

        Returns:
            Updated AdvisorAgent

        Raises:
            ValueError: If agent not found
        """
        agent = await self.db.get(AdvisorAgent, agent_id)
        if not agent:
            raise ValueError("Agent not found")

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(agent, field, value)

        agent.updated_at = datetime.utcnow()
        await self.db.flush()

        logger.info(f"Updated advisor agent {agent_id}")
        return agent

    async def check_permission(
        self,
        agent_id: uuid.UUID,
        action_type: str
    ) -> tuple[bool, str]:
        """
        Check if agent has permission to perform action based on user's autonomy mode.

        Args:
            agent_id: Agent UUID
            action_type: Type of action (suggest, act)

        Returns:
            Tuple of (allowed, reason)
        """
        agent = await self.db.get(AdvisorAgent, agent_id)
        if not agent:
            return False, "Agent not found"

        if not agent.is_enabled:
            return False, "Agent is disabled"

        if agent.status != AgentStatus.ACTIVE:
            return False, f"Agent is not active (status: {agent.status.value})"

        # Get user's founder profile for autonomy mode
        profile = await self.db.get(FounderProfile, agent.user_id)
        if not profile:
            return False, "Founder profile not found"

        autonomy_mode = profile.autonomy_mode.value

        if action_type == "suggest":
            if agent.can_suggest(autonomy_mode):
                return True, "Suggestions allowed"
            return False, f"Suggestions not allowed in {autonomy_mode} mode"

        if action_type == "act":
            if agent.can_act_autonomously(autonomy_mode):
                return True, "Autonomous action allowed"
            return False, f"Autonomous action not allowed in {autonomy_mode} mode"

        return False, f"Unknown action type: {action_type}"

    async def store_memory(
        self,
        agent_id: uuid.UUID,
        memory_data: AgentMemoryCreate
    ) -> AgentMemory:
        """
        Store a new memory for the agent.

        Creates relational record and generates vector embedding in ZeroDB.

        Args:
            agent_id: Agent UUID
            memory_data: Memory creation data

        Returns:
            Created AgentMemory

        Raises:
            ValueError: If agent not found
        """
        agent = await self.db.get(AdvisorAgent, agent_id)
        if not agent:
            raise ValueError("Agent not found")

        # Create memory record
        memory = AgentMemory(
            agent_id=agent_id,
            memory_type=memory_data.memory_type,
            content=memory_data.content,
            summary=memory_data.summary,
            confidence=memory_data.confidence,
            source_type=memory_data.source_type,
            source_id=memory_data.source_id,
            expires_at=memory_data.expires_at
        )

        self.db.add(memory)
        await self.db.flush()

        try:
            # Generate embedding for semantic search
            embedding = await self.embedding_service.generate_embedding(
                memory.embedding_content
            )

            # Store in ZeroDB with agent-scoped namespace
            vector_id = await self.zerodb.upsert_vector(
                entity_type="agent_memory",
                entity_id=memory.id,
                embedding=embedding,
                document=memory.embedding_content,
                metadata=self.zerodb.prepare_metadata(
                    entity_type="agent_memory",
                    source_id=memory.id,
                    user_id=agent.user_id,
                    agent_id=str(agent_id),
                    memory_type=memory.memory_type.value,
                    namespace=agent.memory_namespace
                )
            )

            memory.embedding_id = vector_id

            # Update agent stats
            agent.total_memories += 1
            agent.last_memory_at = datetime.utcnow()

            await self.db.flush()

        except Exception as e:
            logger.warning(f"Failed to create embedding for memory {memory.id}: {e}")
            # Continue without embedding - memory is still stored in relational DB

        logger.info(f"Stored memory {memory.id} for agent {agent_id}")
        return memory

    async def search_memories(
        self,
        agent_id: uuid.UUID,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10
    ) -> List[AgentMemory]:
        """
        Search agent memories using semantic similarity.

        Args:
            agent_id: Agent UUID
            query: Search query
            memory_type: Optional filter by memory type
            limit: Maximum results

        Returns:
            List of matching AgentMemory records
        """
        agent = await self.db.get(AdvisorAgent, agent_id)
        if not agent:
            return []

        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)

            # Build metadata filters
            filters = {
                "agent_id": str(agent_id),
                "namespace": agent.memory_namespace
            }
            if memory_type:
                filters["memory_type"] = memory_type.value

            # Search in ZeroDB
            results = await self.zerodb.search_vectors(
                query_vector=query_embedding,
                entity_type="agent_memory",
                metadata_filters=filters,
                limit=limit
            )

            # Fetch full memory records
            memory_ids = [
                uuid.UUID(r["metadata"]["source_id"])
                for r in results
                if "metadata" in r and "source_id" in r["metadata"]
            ]

            if not memory_ids:
                return []

            stmt = select(AgentMemory).where(AgentMemory.id.in_(memory_ids))
            result = await self.db.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.warning(f"Memory search failed for agent {agent_id}: {e}")
            # Fallback to basic query
            stmt = select(AgentMemory).where(AgentMemory.agent_id == agent_id)
            if memory_type:
                stmt = stmt.where(AgentMemory.memory_type == memory_type)
            stmt = stmt.limit(limit)
            result = await self.db.execute(stmt)
            return list(result.scalars().all())

    async def get_memories(
        self,
        agent_id: uuid.UUID,
        memory_type: Optional[MemoryType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AgentMemory]:
        """
        Get agent memories with optional filtering.

        Args:
            agent_id: Agent UUID
            memory_type: Optional filter by memory type
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of AgentMemory records
        """
        stmt = select(AgentMemory).where(AgentMemory.agent_id == agent_id)

        if memory_type:
            stmt = stmt.where(AgentMemory.memory_type == memory_type)

        stmt = stmt.order_by(AgentMemory.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def generate_weekly_summary(
        self,
        agent_id: uuid.UUID
    ) -> WeeklyOpportunitySummary:
        """
        Generate weekly opportunity summary.

        This is a reproducible summary that includes:
        - Network growth opportunities
        - Potential introductions
        - Goal alignment suggestions
        - Activity highlights

        Args:
            agent_id: Agent UUID

        Returns:
            WeeklyOpportunitySummary

        Raises:
            ValueError: If agent not found
        """
        agent = await self.db.get(AdvisorAgent, agent_id)
        if not agent:
            raise ValueError("Agent not found")

        now = datetime.utcnow()
        period_start = now - timedelta(days=7)
        period_end = now

        # Get recent memories for context
        recent_memories = await self.get_memories(
            agent_id,
            memory_type=MemoryType.OUTCOME,
            limit=20
        )

        # TODO: Implement actual AI-powered summary generation
        # This would use Claude/OpenAI to analyze:
        # - User's goals and asks
        # - Recent interactions and outcomes
        # - Network activity
        # - Potential matches

        suggestions: List[AgentSuggestion] = []
        highlights: List[str] = []
        metrics: Dict[str, Any] = {
            "memories_analyzed": len(recent_memories),
            "period_days": 7
        }

        # Update agent's last summary timestamp
        agent.last_summary_at = now
        await self.db.flush()

        logger.info(f"Generated weekly summary for agent {agent_id}")

        return WeeklyOpportunitySummary(
            generated_at=now,
            period_start=period_start,
            period_end=period_end,
            total_opportunities=len(suggestions),
            suggestions=suggestions,
            highlights=highlights,
            metrics=metrics
        )

    async def record_suggestion(self, agent_id: uuid.UUID) -> None:
        """Record that agent made a suggestion."""
        agent = await self.db.get(AdvisorAgent, agent_id)
        if agent:
            agent.record_suggestion()
            await self.db.flush()

    async def record_action(self, agent_id: uuid.UUID) -> None:
        """Record that agent took an action."""
        agent = await self.db.get(AdvisorAgent, agent_id)
        if agent:
            agent.record_action()
            await self.db.flush()

    async def learn_from_outcome(
        self,
        agent_id: uuid.UUID,
        outcome_type: str,
        success: bool,
        context: Dict[str, Any]
    ) -> AgentMemory:
        """
        Learn from an interaction outcome.

        This creates a memory that the agent can use to improve
        future suggestions.

        Args:
            agent_id: Agent UUID
            outcome_type: Type of outcome (introduction, suggestion, etc.)
            success: Whether the outcome was successful
            context: Additional context about the outcome

        Returns:
            Created AgentMemory
        """
        content = f"Outcome: {outcome_type} - {'Success' if success else 'Failure'}. Context: {context}"
        summary = f"{outcome_type}: {'positive' if success else 'negative'} outcome"

        memory_data = AgentMemoryCreate(
            memory_type=MemoryType.OUTCOME,
            content=content,
            summary=summary,
            confidence=80 if success else 60,
            source_type=outcome_type
        )

        return await self.store_memory(agent_id, memory_data)
