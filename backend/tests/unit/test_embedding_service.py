"""
Unit tests for Embedding Service.
Following TDD principles - tests written BEFORE full implementation.

Test Coverage:
- Embedding generation from text
- Vector upsert to ZeroDB
- Semantic search
- Goal embedding creation
- Ask embedding creation
- Post embedding creation
- Error handling and retries
- Async embedding workflows
- Metadata management
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from app.services.embedding_service import EmbeddingService, EmbeddingServiceError


class TestEmbeddingService:
    """Test Embedding Service functionality."""

    @pytest.fixture
    def embedding_service(self):
        """Create embedding service instance for testing."""
        return EmbeddingService()

    @pytest.fixture
    def mock_embedding_vector(self):
        """Mock 384-dimension embedding vector."""
        return [0.1] * 384

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, embedding_service, mock_embedding_vector):
        """Test successful embedding generation from text."""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock AINative API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "embeddings": [mock_embedding_vector],
                "model": "BAAI/bge-small-en-v1.5",
                "dimensions": 384
            }
            mock_response.raise_for_status = MagicMock()

            # Mock the async context manager and post method
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            text = "Raise $2M seed round by Q2 2025"
            embedding = await embedding_service.generate_embedding(text)

            assert len(embedding) == 384
            assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self, embedding_service):
        """Test embedding generation fails with empty text."""
        with pytest.raises(EmbeddingServiceError, match="empty text"):
            await embedding_service.generate_embedding("")

        with pytest.raises(EmbeddingServiceError, match="empty text"):
            await embedding_service.generate_embedding("   ")

    @pytest.mark.asyncio
    async def test_generate_embedding_api_error(self, embedding_service):
        """Test embedding generation handles API errors."""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock API error
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception("API Error")
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(EmbeddingServiceError):
                await embedding_service.generate_embedding("Test text")

    @pytest.mark.asyncio
    async def test_generate_embedding_wrong_dimensions(self, embedding_service):
        """Test embedding generation fails with wrong dimensions."""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock response with wrong dimensions
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "embeddings": [[0.1] * 512],  # Wrong dimension
                "model": "BAAI/bge-small-en-v1.5",
                "dimensions": 512
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(EmbeddingServiceError, match="Expected 384 dimensions"):
                await embedding_service.generate_embedding("Test text")

    @pytest.mark.asyncio
    async def test_upsert_embedding_success(self, embedding_service, mock_embedding_vector):
        """Test successful embedding upsert to ZeroDB."""
        with patch.object(embedding_service, "generate_embedding", return_value=mock_embedding_vector):
            with patch("httpx.AsyncClient") as mock_client:
                # Mock ZeroDB upsert response
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"vector_id": "goal_123"}
                mock_response.raise_for_status = MagicMock()
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                entity_id = uuid4()
                vector_id = await embedding_service.upsert_embedding(
                    entity_type="goal",
                    entity_id=entity_id,
                    content="Raise funding",
                    metadata={"user_id": str(uuid4()), "goal_type": "fundraising"}
                )

                assert vector_id == "goal_123"

    @pytest.mark.asyncio
    async def test_upsert_embedding_with_retries(self, embedding_service, mock_embedding_vector):
        """Test embedding upsert retries on failure."""
        with patch.object(embedding_service, "generate_embedding", return_value=mock_embedding_vector):
            with patch("httpx.AsyncClient") as mock_client:
                # First two attempts fail, third succeeds
                mock_error_response = MagicMock()
                mock_error_response.raise_for_status.side_effect = Exception("Network error")

                mock_success_response = MagicMock()
                mock_success_response.status_code = 200
                mock_success_response.json.return_value = {"vector_id": "goal_123"}
                mock_success_response.raise_for_status = MagicMock()

                mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=[mock_error_response, mock_error_response, mock_success_response])

                entity_id = uuid4()
                vector_id = await embedding_service.upsert_embedding(
                    entity_type="goal",
                    entity_id=entity_id,
                    content="Test content",
                    metadata={}
                )

                assert vector_id == "goal_123"
                assert mock_client.return_value.__aenter__.return_value.post.call_count == 3  # Retried twice

    @pytest.mark.asyncio
    async def test_search_similar_success(self, embedding_service, mock_embedding_vector):
        """Test semantic search returns results."""
        with patch.object(embedding_service, "generate_embedding", return_value=mock_embedding_vector):
            with patch("httpx.AsyncClient") as mock_client:
                # Mock search results
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "results": [
                        {
                            "vector_id": "goal_1",
                            "similarity": 0.95,
                            "metadata": {"entity_type": "goal", "source_id": str(uuid4())}
                        },
                        {
                            "vector_id": "goal_2",
                            "similarity": 0.87,
                            "metadata": {"entity_type": "goal", "source_id": str(uuid4())}
                        }
                    ]
                }
                mock_response.raise_for_status = MagicMock()
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                results = await embedding_service.search_similar(
                    query_text="Looking for seed funding",
                    entity_type="goal",
                    limit=10
                )

                assert len(results) == 2
                assert results[0]["similarity"] == 0.95
                assert results[1]["similarity"] == 0.87

    @pytest.mark.asyncio
    async def test_create_goal_embedding(self, embedding_service):
        """Test goal-specific embedding creation."""
        with patch.object(embedding_service, "upsert_embedding", return_value="goal_123") as mock_upsert:
            goal_id = uuid4()
            user_id = uuid4()

            vector_id = await embedding_service.create_goal_embedding(
                goal_id=goal_id,
                user_id=user_id,
                goal_type="fundraising",
                description="Raise $2M seed round",
                priority=10
            )

            assert vector_id == "goal_123"
            mock_upsert.assert_called_once()

            # Verify call arguments
            call_args = mock_upsert.call_args
            assert call_args[1]["entity_type"] == "goal"
            assert call_args[1]["entity_id"] == goal_id
            assert "fundraising" in call_args[1]["content"]
            assert call_args[1]["metadata"]["user_id"] == str(user_id)
            assert call_args[1]["metadata"]["goal_type"] == "fundraising"
            assert call_args[1]["metadata"]["priority"] == 10

    @pytest.mark.asyncio
    async def test_create_ask_embedding(self, embedding_service):
        """Test ask-specific embedding creation."""
        with patch.object(embedding_service, "upsert_embedding", return_value="ask_456") as mock_upsert:
            ask_id = uuid4()
            user_id = uuid4()
            goal_id = uuid4()

            vector_id = await embedding_service.create_ask_embedding(
                ask_id=ask_id,
                user_id=user_id,
                description="Need intros to VCs",
                urgency="high",
                goal_id=goal_id
            )

            assert vector_id == "ask_456"
            mock_upsert.assert_called_once()

            # Verify call arguments
            call_args = mock_upsert.call_args
            assert call_args[1]["entity_type"] == "ask"
            assert call_args[1]["entity_id"] == ask_id
            assert "[HIGH]" in call_args[1]["content"]
            assert call_args[1]["metadata"]["urgency"] == "high"
            assert call_args[1]["metadata"]["goal_id"] == str(goal_id)

    @pytest.mark.asyncio
    async def test_create_post_embedding(self, embedding_service):
        """Test post-specific embedding creation."""
        with patch.object(embedding_service, "upsert_embedding", return_value="post_789") as mock_upsert:
            post_id = uuid4()
            user_id = uuid4()

            vector_id = await embedding_service.create_post_embedding(
                post_id=post_id,
                user_id=user_id,
                post_type="milestone",
                content="Just closed our first customer!"
            )

            assert vector_id == "post_789"
            mock_upsert.assert_called_once()

            # Verify call arguments
            call_args = mock_upsert.call_args
            assert call_args[1]["entity_type"] == "post"
            assert call_args[1]["entity_id"] == post_id
            assert "[MILESTONE]" in call_args[1]["content"]
            assert call_args[1]["metadata"]["post_type"] == "milestone"

    @pytest.mark.asyncio
    async def test_delete_embedding_success(self, embedding_service):
        """Test embedding deletion."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_response)

            result = await embedding_service.delete_embedding("goal_123")
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_embedding_failure(self, embedding_service):
        """Test embedding deletion handles errors gracefully."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception("Not found")
            mock_client.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_response)

            result = await embedding_service.delete_embedding("nonexistent")
            assert result is False

    @pytest.mark.asyncio
    async def test_discover_relevant_posts(self, embedding_service, mock_embedding_vector):
        """Test post discovery with recency weighting."""
        with patch.object(embedding_service, "generate_embedding", return_value=mock_embedding_vector):
            with patch.object(embedding_service, "search_similar") as mock_search:
                # Mock search results with timestamps
                mock_search.return_value = [
                    {
                        "vector_id": "post_1",
                        "similarity": 0.9,
                        "metadata": {
                            "entity_type": "post",
                            "timestamp": "2025-01-15T10:00:00Z"
                        }
                    },
                    {
                        "vector_id": "post_2",
                        "similarity": 0.8,
                        "metadata": {
                            "entity_type": "post",
                            "timestamp": "2025-01-14T10:00:00Z"
                        }
                    }
                ]

                user_goals = ["Raise funding", "Hire engineers"]
                results = await embedding_service.discover_relevant_posts(
                    user_goals=user_goals,
                    limit=10,
                    recency_weight=0.3
                )

                assert len(results) <= 10
                assert all(isinstance(result, tuple) for result in results)
                # Each result should be (data, combined_score)
                assert all(len(result) == 2 for result in results)

    @pytest.mark.asyncio
    async def test_search_with_metadata_filters(self, embedding_service, mock_embedding_vector):
        """Test search with metadata filtering."""
        with patch.object(embedding_service, "generate_embedding", return_value=mock_embedding_vector):
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"results": []}
                mock_response.raise_for_status = MagicMock()
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                await embedding_service.search_similar(
                    query_text="Test query",
                    entity_type="goal",
                    metadata_filters={"user_id": str(uuid4()), "goal_type": "fundraising"},
                    limit=5
                )

                # Verify metadata filters were passed
                call_args = mock_post.call_args
                payload = call_args[1]["json"]
                assert "filter_metadata" in payload
                assert payload["filter_metadata"]["entity_type"] == "goal"
                assert "goal_type" in payload["filter_metadata"]
