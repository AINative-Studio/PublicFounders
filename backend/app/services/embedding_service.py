"""
Embedding Service - Integrates with ZeroDB for semantic vector storage.

This service handles:
1. Generating embeddings from text content
2. Storing embeddings in ZeroDB with metadata
3. Semantic search across entity types
4. Async/sync embedding strategies

Architecture:
- Synchronous for Goals & Asks (critical for matching)
- Asynchronous for Posts (don't block user experience)
- Retry logic with exponential backoff
- Graceful degradation on failures
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency
_observability_service = None

def get_observability_service():
    """Lazy load observability service to avoid circular imports."""
    global _observability_service
    if _observability_service is None:
        from app.services.observability_service import observability_service
        _observability_service = observability_service
    return _observability_service


class EmbeddingServiceError(Exception):
    """Base exception for embedding service errors."""
    pass


class EmbeddingService:
    """
    Manages semantic embeddings using ZeroDB vector storage.

    Key Features:
    - AINative 384-dimension embeddings (BAAI/bge-small-en-v1.5)
    - Metadata-rich vector storage
    - Semantic search with filtering
    - Retry logic for resilience
    """

    EMBEDDING_DIMENSION = 384
    NAMESPACE = "publicfounders"
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds

    def __init__(self):
        """Initialize embedding service with AINative/ZeroDB configuration."""
        self.ainative_api_key = settings.AINATIVE_API_KEY
        self.ainative_base_url = settings.AINATIVE_API_BASE_URL
        self.zerodb_project_id = settings.ZERODB_PROJECT_ID
        self.zerodb_api_key = settings.ZERODB_API_KEY
        self.base_url = f"https://api.ainative.studio/v1/public/{self.zerodb_project_id}"

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector from text using AINative Embeddings API.

        Args:
            text: Input text to embed

        Returns:
            List of floats (384 dimensions)

        Raises:
            EmbeddingServiceError: If embedding generation fails
        """
        if not text or not text.strip():
            raise EmbeddingServiceError("Cannot generate embedding from empty text")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ainative_base_url}v1/public/embeddings/generate",
                    headers={
                        "X-API-Key": self.ainative_api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "texts": [text.strip()],
                        "model": "BAAI/bge-small-en-v1.5",
                        "normalize": True
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                embedding = data["embeddings"][0]

                if len(embedding) != self.EMBEDDING_DIMENSION:
                    raise EmbeddingServiceError(
                        f"Expected {self.EMBEDDING_DIMENSION} dimensions, got {len(embedding)}"
                    )

                # Track embedding cost (approx. token count)
                token_count = len(text.split()) * 1.3  # Rough estimate
                obs_service = get_observability_service()
                await obs_service.track_embedding_cost(
                    operation="generate",
                    tokens=int(token_count),
                    model="BAAI/bge-small-en-v1.5"
                )

                return embedding

        except httpx.HTTPError as e:
            logger.error(f"AINative Embeddings API error: {e}")
            raise EmbeddingServiceError(f"Failed to generate embedding: {e}")
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}")
            raise EmbeddingServiceError(f"Unexpected error: {e}")

    async def upsert_embedding(
        self,
        entity_type: str,
        entity_id: UUID,
        content: str,
        metadata: Dict[str, Any],
        vector_id: Optional[str] = None
    ) -> str:
        """
        Create or update an embedding in ZeroDB.

        Args:
            entity_type: Type of entity (goal, ask, post, etc.)
            entity_id: UUID of the source entity
            content: Text content to embed
            metadata: Additional metadata for filtering
            vector_id: Optional existing vector ID for updates

        Returns:
            Vector ID from ZeroDB

        Raises:
            EmbeddingServiceError: If operation fails after retries
        """
        embedding = await self.generate_embedding(content)

        # Prepare metadata with required fields
        full_metadata = {
            "entity_type": entity_type,
            "source_id": str(entity_id),
            "timestamp": datetime.utcnow().isoformat(),
            **metadata
        }

        # Retry logic for ZeroDB upsert
        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/vectors/upsert",
                        headers={
                            "X-Project-ID": self.zerodb_project_id,
                            "X-API-Key": self.zerodb_api_key,
                            "Content-Type": "application/json"
                        },
                        json={
                            "vector_id": vector_id or f"{entity_type}_{entity_id}",
                            "vector_embedding": embedding,
                            "document": content,
                            "metadata": full_metadata,
                            "namespace": self.NAMESPACE
                        },
                        timeout=30.0
                    )
                    response.raise_for_status()
                    result = response.json()

                    logger.info(
                        f"Successfully upserted embedding for {entity_type} {entity_id}"
                    )
                    return result.get("vector_id", f"{entity_type}_{entity_id}")

            except httpx.HTTPError as e:
                logger.warning(
                    f"ZeroDB upsert attempt {attempt + 1} failed: {e}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (2 ** attempt))
                else:
                    raise EmbeddingServiceError(f"Failed to upsert embedding after {self.MAX_RETRIES} attempts: {e}")
            except Exception as e:
                logger.error(f"Unexpected error upserting embedding: {e}")
                raise EmbeddingServiceError(f"Unexpected error: {e}")

    async def search_similar(
        self,
        query_text: str,
        entity_type: Optional[str] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar entities.

        Args:
            query_text: Search query
            entity_type: Optional filter by entity type
            metadata_filters: Optional metadata filters
            limit: Maximum results to return
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of matching entities with similarity scores
        """
        query_embedding = await self.generate_embedding(query_text)

        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "query_vector": query_embedding,
                    "limit": limit,
                    "threshold": min_similarity,
                    "namespace": self.NAMESPACE
                }

                # Add metadata filters
                if entity_type or metadata_filters:
                    filters = metadata_filters or {}
                    if entity_type:
                        filters["entity_type"] = entity_type
                    payload["filter_metadata"] = filters

                response = await client.post(
                    f"{self.base_url}/vectors/search",
                    headers={
                        "X-Project-ID": self.zerodb_project_id,
                        "X-API-Key": self.zerodb_api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                results = response.json()

                logger.info(
                    f"Found {len(results.get('results', []))} similar entities"
                )
                return results.get("results", [])

        except httpx.HTTPError as e:
            logger.error(f"Search failed: {e}")
            raise EmbeddingServiceError(f"Search failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected search error: {e}")
            raise EmbeddingServiceError(f"Unexpected error: {e}")

    async def delete_embedding(self, vector_id: str) -> bool:
        """
        Delete an embedding from ZeroDB.

        Args:
            vector_id: ID of vector to delete

        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/vectors/{vector_id}",
                    headers={
                        "X-Project-ID": self.zerodb_project_id,
                        "X-API-Key": self.zerodb_api_key
                    },
                    params={"namespace": self.NAMESPACE},
                    timeout=30.0
                )
                response.raise_for_status()
                logger.info(f"Deleted embedding {vector_id}")
                return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to delete embedding: {e}")
            return False

    async def create_goal_embedding(
        self,
        goal_id: UUID,
        user_id: UUID,
        goal_type: str,
        description: str,
        priority: int,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create embedding for a goal (synchronous - critical for matching).

        Args:
            goal_id: Goal UUID
            user_id: User UUID
            goal_type: Goal category
            description: Goal description
            priority: Priority level
            additional_metadata: Extra metadata

        Returns:
            Vector ID
        """
        content = f"{goal_type}: {description}"
        metadata = {
            "user_id": str(user_id),
            "goal_type": goal_type,
            "priority": priority,
            **(additional_metadata or {})
        }

        return await self.upsert_embedding(
            entity_type="goal",
            entity_id=goal_id,
            content=content,
            metadata=metadata
        )

    async def create_ask_embedding(
        self,
        ask_id: UUID,
        user_id: UUID,
        description: str,
        urgency: str,
        goal_id: Optional[UUID] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create embedding for an ask (synchronous - critical for matching).

        Args:
            ask_id: Ask UUID
            user_id: User UUID
            description: Ask description
            urgency: Urgency level
            goal_id: Optional linked goal
            additional_metadata: Extra metadata

        Returns:
            Vector ID
        """
        urgency_prefix = f"[{urgency.upper()}] " if urgency != "medium" else ""
        content = f"{urgency_prefix}{description}"

        metadata = {
            "user_id": str(user_id),
            "urgency": urgency,
            **(additional_metadata or {})
        }

        if goal_id:
            metadata["goal_id"] = str(goal_id)

        return await self.upsert_embedding(
            entity_type="ask",
            entity_id=ask_id,
            content=content,
            metadata=metadata
        )

    async def create_post_embedding(
        self,
        post_id: UUID,
        user_id: UUID,
        post_type: str,
        content: str,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create embedding for a post (can be async - don't block UX).

        Args:
            post_id: Post UUID
            user_id: User UUID
            post_type: Post category
            content: Post content
            additional_metadata: Extra metadata

        Returns:
            Vector ID
        """
        embedding_content = f"[{post_type.upper()}] {content}"
        metadata = {
            "user_id": str(user_id),
            "post_type": post_type,
            **(additional_metadata or {})
        }

        return await self.upsert_embedding(
            entity_type="post",
            entity_id=post_id,
            content=embedding_content,
            metadata=metadata
        )

    async def create_profile_embedding(
        self,
        user: Any,  # User model
        profile: Any  # FounderProfile model
    ) -> str:
        """
        Create embedding for a founder profile.

        Args:
            user: User model instance
            profile: FounderProfile model instance

        Returns:
            Vector ID
        """
        # Compose content from user and profile data
        content_parts = []

        if user.name:
            content_parts.append(f"Name: {user.name}")

        if user.headline:
            content_parts.append(f"Headline: {user.headline}")

        if user.location:
            content_parts.append(f"Location: {user.location}")

        if profile.bio:
            content_parts.append(f"Bio: {profile.bio}")

        if profile.current_focus:
            content_parts.append(f"Current Focus: {profile.current_focus}")

        content = "\n".join(content_parts)

        # Prepare metadata
        metadata = {
            "user_id": str(user.id),
            "name": user.name or "",
            "location": user.location or "",
            "headline": user.headline or "",
            "autonomy_mode": profile.autonomy_mode.value if profile.autonomy_mode else "suggest",
            "public_visibility": profile.public_visibility
        }

        # Use existing embedding_id if available (for updates)
        vector_id = profile.embedding_id if hasattr(profile, 'embedding_id') and profile.embedding_id else None

        return await self.upsert_embedding(
            entity_type="founder",
            entity_id=user.id,
            content=content,
            metadata=metadata,
            vector_id=vector_id
        )

    async def discover_relevant_posts(
        self,
        user_goals: List[str],
        limit: int = 20,
        recency_weight: float = 0.3
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Discover posts relevant to user's goals with recency weighting.

        Args:
            user_goals: List of user goal descriptions
            limit: Max results
            recency_weight: Weight for recency (0-1)

        Returns:
            List of (post_data, combined_score) tuples
        """
        # Combine user goals for query
        query = " ".join(user_goals)

        # Search for similar posts
        results = await self.search_similar(
            query_text=query,
            entity_type="post",
            limit=limit * 2,  # Get more to allow for recency filtering
            min_similarity=0.5
        )

        # Calculate combined score (similarity + recency)
        scored_results = []
        current_time = datetime.utcnow()

        for result in results:
            similarity = result.get("similarity", 0.0)
            timestamp_str = result.get("metadata", {}).get("timestamp")

            # Calculate recency score (decay over time)
            recency_score = 0.5  # Default
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    hours_old = (current_time - timestamp).total_seconds() / 3600
                    # Exponential decay: fresh posts score higher
                    recency_score = max(0.0, 1.0 - (hours_old / 720))  # 30 days
                except Exception:
                    pass

            # Combined score
            combined_score = (
                similarity * (1 - recency_weight) +
                recency_score * recency_weight
            )

            scored_results.append((result, combined_score))

        # Sort by combined score and return top results
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results[:limit]


# Singleton instance
embedding_service = EmbeddingService()
