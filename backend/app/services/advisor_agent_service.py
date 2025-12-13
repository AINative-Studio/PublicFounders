"""
Advisor Agent Service
Handles AI advisor agent lifecycle and operations using ZeroDB NoSQL + Vectors.
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from app.models.advisor_agent import AgentStatus, MemoryType
from app.schemas.advisor_agent import (
    AgentMemoryCreate,
    AdvisorAgentUpdate,
    AgentSuggestion,
    WeeklyOpportunitySummary
)
from app.services.zerodb_service import zerodb_service
from app.services.zerodb_client import zerodb_client
from app.services.embedding_service import embedding_service
from app.core.enums import AutonomyMode

logger = logging.getLogger(__name__)


class AdvisorAgentService:
    """
    Service for advisor agent management using ZeroDB.

    Each founder has one advisor agent that:
    - Has isolated memory (scoped by agent_id in ZeroDB vectors)
    - Cannot act without checking user's autonomy_mode permissions
    - Generates weekly opportunity summaries
    - Learns from interaction outcomes

    Data Storage:
    - Agent records: ZeroDB NoSQL table 'advisor_agents'
    - Agent memories: ZeroDB NoSQL table 'agent_memories'
    - Semantic search: ZeroDB vectors with agent-scoped namespaces
    """

    def __init__(self):
        """Initialize advisor agent service with ZeroDB clients."""
        self.zerodb = zerodb_service
        self.zerodb_client = zerodb_client
        self.embedding_service = embedding_service

    async def initialize_agent(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        Initialize a new advisor agent for a user.

        Creates the agent in INITIALIZING status and sets up
        isolated memory namespace in ZeroDB.

        Args:
            user_id: User UUID

        Returns:
            Newly created agent dictionary

        Raises:
            ValueError: If user not found or already has an agent
        """
        user_id_str = str(user_id)

        # Verify user exists
        user = await self.zerodb_client.get_by_id("users", user_id_str)
        if not user:
            raise ValueError("User not found")

        # Check for existing agent
        existing = await self.get_agent_by_user_id(user_id)
        if existing:
            raise ValueError("User already has an advisor agent")

        # Create agent with isolated memory namespace
        agent_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        agent_data = {
            "id": agent_id,
            "user_id": user_id_str,
            "status": AgentStatus.INITIALIZING.value,
            "name": "Advisor",
            "description": None,
            "memory_namespace": f"agent_{user_id_str}",
            "total_memories": 0,
            "last_memory_at": None,
            "last_active_at": None,
            "last_summary_at": None,
            "total_suggestions": 0,
            "total_actions": 0,
            "is_enabled": True,
            "created_at": now,
            "updated_at": now
        }

        await self.zerodb_client.insert_rows("advisor_agents", [agent_data])
        logger.info(f"Initialized advisor agent {agent_id} for user {user_id}")

        return agent_data

    async def get_agent_by_user_id(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get advisor agent by user ID.

        Args:
            user_id: User UUID

        Returns:
            Agent dictionary if found, None otherwise
        """
        agents = await self.zerodb_client.query_rows(
            table_name="advisor_agents",
            filter={"user_id": str(user_id)},
            limit=1
        )
        return agents[0] if agents else None

    async def get_agent(self, agent_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get advisor agent by ID.

        Args:
            agent_id: Agent UUID

        Returns:
            Agent dictionary if found, None otherwise
        """
        return await self.zerodb_client.get_by_id("advisor_agents", str(agent_id))

    async def activate_agent(self, agent_id: uuid.UUID) -> Dict[str, Any]:
        """
        Activate an advisor agent.

        Args:
            agent_id: Agent UUID

        Returns:
            Updated agent dictionary

        Raises:
            ValueError: If agent not found
        """
        agent = await self.get_agent(agent_id)
        if not agent:
            raise ValueError("Agent not found")

        now = datetime.utcnow().isoformat()
        update_data = {
            "status": AgentStatus.ACTIVE.value,
            "last_active_at": now,
            "updated_at": now
        }

        await self.zerodb_client.update_rows(
            table_name="advisor_agents",
            filter={"id": str(agent_id)},
            update={"$set": update_data}
        )

        agent.update(update_data)
        logger.info(f"Activated advisor agent {agent_id}")
        return agent

    async def deactivate_agent(self, agent_id: uuid.UUID) -> Dict[str, Any]:
        """
        Deactivate an advisor agent.

        Args:
            agent_id: Agent UUID

        Returns:
            Updated agent dictionary

        Raises:
            ValueError: If agent not found
        """
        agent = await self.get_agent(agent_id)
        if not agent:
            raise ValueError("Agent not found")

        now = datetime.utcnow().isoformat()
        update_data = {
            "status": AgentStatus.DEACTIVATED.value,
            "updated_at": now
        }

        await self.zerodb_client.update_rows(
            table_name="advisor_agents",
            filter={"id": str(agent_id)},
            update={"$set": update_data}
        )

        agent.update(update_data)
        logger.info(f"Deactivated advisor agent {agent_id}")
        return agent

    async def update_agent(
        self,
        agent_id: uuid.UUID,
        update_data: AdvisorAgentUpdate
    ) -> Dict[str, Any]:
        """
        Update advisor agent settings.

        Args:
            agent_id: Agent UUID
            update_data: Update data

        Returns:
            Updated agent dictionary

        Raises:
            ValueError: If agent not found
        """
        agent = await self.get_agent(agent_id)
        if not agent:
            raise ValueError("Agent not found")

        update_dict = update_data.model_dump(exclude_unset=True)
        update_dict["updated_at"] = datetime.utcnow().isoformat()

        await self.zerodb_client.update_rows(
            table_name="advisor_agents",
            filter={"id": str(agent_id)},
            update={"$set": update_dict}
        )

        agent.update(update_dict)
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
        agent = await self.get_agent(agent_id)
        if not agent:
            return False, "Agent not found"

        if not agent.get("is_enabled", False):
            return False, "Agent is disabled"

        status = agent.get("status")
        if status != AgentStatus.ACTIVE.value:
            return False, f"Agent is not active (status: {status})"

        # Get user's founder profile for autonomy mode
        profiles = await self.zerodb_client.query_rows(
            table_name="founder_profiles",
            filter={"user_id": agent.get("user_id")},
            limit=1
        )

        if not profiles:
            return False, "Founder profile not found"

        profile = profiles[0]
        autonomy_mode = profile.get("autonomy_mode", AutonomyMode.SUGGEST.value)

        if action_type == "suggest":
            if autonomy_mode in (AutonomyMode.SUGGEST.value, AutonomyMode.APPROVE.value, AutonomyMode.AUTO.value):
                return True, "Suggestions allowed"
            return False, f"Suggestions not allowed in {autonomy_mode} mode"

        if action_type == "act":
            if autonomy_mode == AutonomyMode.AUTO.value:
                return True, "Autonomous action allowed"
            return False, f"Autonomous action not allowed in {autonomy_mode} mode"

        return False, f"Unknown action type: {action_type}"

    async def store_memory(
        self,
        agent_id: uuid.UUID,
        memory_data: AgentMemoryCreate
    ) -> Dict[str, Any]:
        """
        Store a new memory for the agent.

        Creates NoSQL record and generates vector embedding in ZeroDB.

        Args:
            agent_id: Agent UUID
            memory_data: Memory creation data

        Returns:
            Created memory dictionary

        Raises:
            ValueError: If agent not found
        """
        agent = await self.get_agent(agent_id)
        if not agent:
            raise ValueError("Agent not found")

        agent_id_str = str(agent_id)
        memory_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        # Prepare memory content for embedding
        embedding_content = f"{memory_data.memory_type.value}: {memory_data.content}"

        # Create memory record
        memory = {
            "id": memory_id,
            "agent_id": agent_id_str,
            "memory_type": memory_data.memory_type.value,
            "content": memory_data.content,
            "summary": memory_data.summary,
            "embedding_id": None,
            "confidence": memory_data.confidence,
            "source_type": memory_data.source_type,
            "source_id": str(memory_data.source_id) if memory_data.source_id else None,
            "created_at": now,
            "expires_at": memory_data.expires_at.isoformat() if memory_data.expires_at else None
        }

        try:
            # Generate embedding for semantic search
            embedding = await self.embedding_service.generate_embedding(embedding_content)

            # Store in ZeroDB vectors with agent-scoped namespace
            vector_id = await self.zerodb.upsert_vector(
                entity_type="agent_memory",
                entity_id=uuid.UUID(memory_id),
                embedding=embedding,
                document=embedding_content,
                metadata=self.zerodb.prepare_metadata(
                    entity_type="agent_memory",
                    source_id=uuid.UUID(memory_id),
                    user_id=uuid.UUID(agent.get("user_id")),
                    agent_id=agent_id_str,
                    memory_type=memory_data.memory_type.value,
                    namespace=agent.get("memory_namespace")
                )
            )

            memory["embedding_id"] = vector_id

        except Exception as e:
            logger.warning(f"Failed to create embedding for memory {memory_id}: {e}")
            # Continue without embedding - memory is still stored in NoSQL

        # Insert memory record
        await self.zerodb_client.insert_rows("agent_memories", [memory])

        # Update agent stats
        agent_now = datetime.utcnow().isoformat()
        await self.zerodb_client.update_rows(
            table_name="advisor_agents",
            filter={"id": agent_id_str},
            update={
                "$set": {
                    "total_memories": agent.get("total_memories", 0) + 1,
                    "last_memory_at": agent_now,
                    "updated_at": agent_now
                }
            }
        )

        logger.info(f"Stored memory {memory_id} for agent {agent_id}")
        return memory

    async def search_memories(
        self,
        agent_id: uuid.UUID,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search agent memories using semantic similarity.

        Args:
            agent_id: Agent UUID
            query: Search query
            memory_type: Optional filter by memory type
            limit: Maximum results

        Returns:
            List of matching memory records
        """
        agent = await self.get_agent(agent_id)
        if not agent:
            return []

        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)

            # Build metadata filters
            filters = {
                "agent_id": str(agent_id),
                "namespace": agent.get("memory_namespace")
            }
            if memory_type:
                filters["memory_type"] = memory_type.value

            # Search in ZeroDB vectors
            results = await self.zerodb.search_vectors(
                query_vector=query_embedding,
                entity_type="agent_memory",
                metadata_filters=filters,
                limit=limit
            )

            # Fetch full memory records
            memory_ids = [
                r["metadata"]["source_id"]
                for r in results
                if "metadata" in r and "source_id" in r["metadata"]
            ]

            if not memory_ids:
                return []

            # Query memories by IDs
            memories = []
            for mid in memory_ids:
                memory = await self.zerodb_client.get_by_id("agent_memories", mid)
                if memory:
                    memories.append(memory)

            return memories

        except Exception as e:
            logger.warning(f"Memory search failed for agent {agent_id}: {e}")
            # Fallback to basic query
            return await self.get_memories(agent_id, memory_type, limit)

    async def get_memories(
        self,
        agent_id: uuid.UUID,
        memory_type: Optional[MemoryType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get agent memories with optional filtering.

        Args:
            agent_id: Agent UUID
            memory_type: Optional filter by memory type
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of memory records
        """
        filter_query = {"agent_id": str(agent_id)}
        if memory_type:
            filter_query["memory_type"] = memory_type.value

        memories = await self.zerodb_client.query_rows(
            table_name="agent_memories",
            filter=filter_query,
            limit=limit,
            offset=offset,
            sort={"created_at": -1}  # Newest first
        )

        return memories

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
        agent = await self.get_agent(agent_id)
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
        now_iso = now.isoformat()
        await self.zerodb_client.update_rows(
            table_name="advisor_agents",
            filter={"id": str(agent_id)},
            update={"$set": {"last_summary_at": now_iso, "updated_at": now_iso}}
        )

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
        agent = await self.get_agent(agent_id)
        if agent:
            now = datetime.utcnow().isoformat()
            await self.zerodb_client.update_rows(
                table_name="advisor_agents",
                filter={"id": str(agent_id)},
                update={
                    "$set": {
                        "total_suggestions": agent.get("total_suggestions", 0) + 1,
                        "last_active_at": now,
                        "updated_at": now
                    }
                }
            )

    async def record_action(self, agent_id: uuid.UUID) -> None:
        """Record that agent took an action."""
        agent = await self.get_agent(agent_id)
        if agent:
            now = datetime.utcnow().isoformat()
            await self.zerodb_client.update_rows(
                table_name="advisor_agents",
                filter={"id": str(agent_id)},
                update={
                    "$set": {
                        "total_actions": agent.get("total_actions", 0) + 1,
                        "last_active_at": now,
                        "updated_at": now
                    }
                }
            )

    async def learn_from_outcome(
        self,
        agent_id: uuid.UUID,
        outcome_type: str,
        success: bool,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
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
            Created memory dictionary
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


# Singleton instance for stateless service
advisor_agent_service = AdvisorAgentService()
