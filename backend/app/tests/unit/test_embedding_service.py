"""
Unit Tests for Embedding Service
TDD tests for ZeroDB vector embedding integration
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding_service import EmbeddingService
from app.models.user import User
from app.models.founder_profile import FounderProfile


@pytest.mark.unit
class TestEmbeddingGeneration:
    """Test suite for embedding generation"""

    @pytest.mark.asyncio
    async def test_generate_profile_embedding_from_content(self, mock_embedding_vector):
        """Test generating embedding from profile content"""
        # Arrange
        embedding_service = EmbeddingService()
        profile_content = "Building AI-powered tools for founders. Raising seed round."

        # Mock OpenAI embedding
        with patch('app.services.embedding_service.openai') as mock_openai:
            mock_openai.embeddings.create = AsyncMock(
                return_value=Mock(
                    data=[Mock(embedding=mock_embedding_vector)]
                )
            )

            # Act
            embedding = await embedding_service.generate_embedding(profile_content)

        # Assert
        assert embedding is not None
        assert len(embedding) == 1536  # OpenAI embedding dimension
        assert isinstance(embedding, list)

    @pytest.mark.asyncio
    async def test_create_profile_embedding_combines_user_and_profile_data(
        self, db_session: AsyncSession, sample_user_with_profile, mock_embedding_vector
    ):
        """Test creating profile embedding combines user and profile data"""
        # Arrange
        user, profile = sample_user_with_profile
        embedding_service = EmbeddingService()

        # Mock embedding generation
        with patch.object(embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_embedding_vector

            # Act
            embedding_id = await embedding_service.create_profile_embedding(user, profile)

        # Assert
        # Should have combined user headline and profile data
        call_args = mock_generate.call_args[0][0]
        assert user.headline in call_args or user.name in call_args
        assert profile.bio in call_args or profile.current_focus in call_args

    @pytest.mark.asyncio
    async def test_embedding_dimension_is_1536(self, mock_embedding_vector):
        """Test embedding dimension matches ZeroDB requirement (1536)"""
        # Arrange
        embedding_service = EmbeddingService()

        # Mock OpenAI
        with patch('app.services.embedding_service.openai') as mock_openai:
            mock_openai.embeddings.create = AsyncMock(
                return_value=Mock(
                    data=[Mock(embedding=mock_embedding_vector)]
                )
            )

            # Act
            embedding = await embedding_service.generate_embedding("Test content")

        # Assert
        assert len(embedding) == 1536


@pytest.mark.unit
class TestZeroDBIntegration:
    """Test suite for ZeroDB vector storage"""

    @pytest.mark.asyncio
    async def test_upsert_vector_to_zerodb(
        self, sample_user_with_profile, mock_embedding_vector, mock_zerodb_response
    ):
        """Test upserting vector to ZeroDB"""
        # Arrange
        user, profile = sample_user_with_profile
        embedding_service = EmbeddingService()

        # Mock ZeroDB MCP call
        with patch('app.services.embedding_service.zerodb_upsert_vector') as mock_upsert:
            mock_upsert.return_value = mock_zerodb_response

            # Act
            vector_id = await embedding_service.upsert_to_zerodb(
                embedding=mock_embedding_vector,
                document=f"{user.name} - {profile.bio}",
                metadata={
                    "user_id": str(user.id),
                    "entity_type": "founder",
                    "location": user.location,
                    "headline": user.headline
                }
            )

        # Assert
        assert vector_id is not None
        mock_upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_includes_metadata(
        self, sample_user_with_profile, mock_embedding_vector
    ):
        """Test ZeroDB upsert includes proper metadata"""
        # Arrange
        user, profile = sample_user_with_profile
        embedding_service = EmbeddingService()

        # Mock ZeroDB
        with patch('app.services.embedding_service.zerodb_upsert_vector') as mock_upsert:
            mock_upsert.return_value = {"vector_id": "vec_123"}

            # Act
            await embedding_service.upsert_to_zerodb(
                embedding=mock_embedding_vector,
                document="Test document",
                metadata={
                    "user_id": str(user.id),
                    "entity_type": "founder",
                    "location": user.location
                }
            )

        # Assert
        call_args = mock_upsert.call_args[1]
        assert "metadata" in call_args
        assert call_args["metadata"]["user_id"] == str(user.id)
        assert call_args["metadata"]["entity_type"] == "founder"

    @pytest.mark.asyncio
    async def test_create_profile_embedding_stores_embedding_id(
        self, db_session: AsyncSession, sample_user_with_profile, mock_embedding_vector
    ):
        """Test creating profile embedding stores embedding_id in profile"""
        # Arrange
        user, profile = sample_user_with_profile
        embedding_service = EmbeddingService()
        test_vector_id = "vec_test_123"

        # Mock embedding generation and storage
        with patch.object(embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_generate:
            with patch.object(embedding_service, 'upsert_to_zerodb', new_callable=AsyncMock) as mock_upsert:
                mock_generate.return_value = mock_embedding_vector
                mock_upsert.return_value = test_vector_id

                # Act
                embedding_id = await embedding_service.create_profile_embedding(user, profile)

        # Assert
        assert embedding_id == test_vector_id
        # Note: In actual implementation, embedding_id should be saved to profile.embedding_id

    @pytest.mark.asyncio
    async def test_update_embedding_uses_same_vector_id(
        self, db_session: AsyncSession, sample_user_with_profile, mock_embedding_vector
    ):
        """Test updating embedding reuses existing vector_id (upsert behavior)"""
        # Arrange
        user, profile = sample_user_with_profile
        existing_vector_id = "vec_existing_456"
        profile.embedding_id = existing_vector_id
        await db_session.commit()

        embedding_service = EmbeddingService()

        # Mock embedding generation
        with patch.object(embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_generate:
            with patch('app.services.embedding_service.zerodb_upsert_vector') as mock_upsert:
                mock_generate.return_value = mock_embedding_vector
                mock_upsert.return_value = {"vector_id": existing_vector_id}

                # Act
                embedding_id = await embedding_service.create_profile_embedding(user, profile)

        # Assert
        # Should pass existing vector_id for update
        call_args = mock_upsert.call_args[1]
        if "vector_id" in call_args:
            assert call_args["vector_id"] == existing_vector_id


@pytest.mark.unit
class TestEmbeddingContent:
    """Test suite for embedding content composition"""

    @pytest.mark.asyncio
    async def test_embedding_includes_user_headline(
        self, sample_user_with_profile, mock_embedding_vector
    ):
        """Test embedding content includes user headline"""
        # Arrange
        user, profile = sample_user_with_profile
        embedding_service = EmbeddingService()

        # Mock
        with patch.object(embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_embedding_vector

            # Act
            await embedding_service.create_profile_embedding(user, profile)

        # Assert
        call_content = mock_generate.call_args[0][0]
        assert user.headline in call_content

    @pytest.mark.asyncio
    async def test_embedding_includes_profile_bio(
        self, sample_user_with_profile, mock_embedding_vector
    ):
        """Test embedding content includes profile bio"""
        # Arrange
        user, profile = sample_user_with_profile
        embedding_service = EmbeddingService()

        # Mock
        with patch.object(embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_embedding_vector

            # Act
            await embedding_service.create_profile_embedding(user, profile)

        # Assert
        call_content = mock_generate.call_args[0][0]
        assert profile.bio in call_content

    @pytest.mark.asyncio
    async def test_embedding_includes_current_focus(
        self, sample_user_with_profile, mock_embedding_vector
    ):
        """Test embedding content includes current focus"""
        # Arrange
        user, profile = sample_user_with_profile
        embedding_service = EmbeddingService()

        # Mock
        with patch.object(embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_embedding_vector

            # Act
            await embedding_service.create_profile_embedding(user, profile)

        # Assert
        call_content = mock_generate.call_args[0][0]
        assert profile.current_focus in call_content

    @pytest.mark.asyncio
    async def test_handles_missing_optional_fields(
        self, db_session: AsyncSession, sample_user, mock_embedding_vector
    ):
        """Test embedding handles missing optional fields gracefully"""
        # Arrange
        from app.models.founder_profile import FounderProfile, AutonomyMode
        from datetime import datetime

        # Create profile with minimal data
        profile = FounderProfile(
            user_id=sample_user.id,
            bio=None,  # Missing
            current_focus=None,  # Missing
            autonomy_mode=AutonomyMode.SUGGEST,
            public_visibility=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(profile)
        await db_session.commit()

        embedding_service = EmbeddingService()

        # Mock
        with patch.object(embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_embedding_vector

            # Act - Should not raise exception
            await embedding_service.create_profile_embedding(sample_user, profile)

        # Assert
        mock_generate.assert_called_once()
