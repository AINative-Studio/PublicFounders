"""
Unit Tests for Profile Service
TDD tests for founder profile creation and updates
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.profile_service import ProfileService
from app.models.user import User
from app.models.founder_profile import FounderProfile, AutonomyMode
from app.schemas.founder_profile import FounderProfileUpdate


@pytest.mark.unit
class TestProfileCreation:
    """Test suite for profile creation"""

    @pytest.mark.asyncio
    async def test_get_profile_by_user_id(self, db_session: AsyncSession, sample_user_with_profile):
        """Test retrieving profile by user ID"""
        # Arrange
        user, profile = sample_user_with_profile
        profile_service = ProfileService(db_session)

        # Act
        retrieved_profile = await profile_service.get_profile(user.id)

        # Assert
        assert retrieved_profile is not None
        assert retrieved_profile.user_id == user.id
        assert retrieved_profile.bio == profile.bio

    @pytest.mark.asyncio
    async def test_get_nonexistent_profile_returns_none(self, db_session: AsyncSession):
        """Test retrieving non-existent profile returns None"""
        # Arrange
        import uuid
        profile_service = ProfileService(db_session)
        nonexistent_user_id = uuid.uuid4()

        # Act
        profile = await profile_service.get_profile(nonexistent_user_id)

        # Assert
        assert profile is None


@pytest.mark.unit
class TestProfileUpdate:
    """Test suite for profile updates"""

    @pytest.mark.asyncio
    async def test_update_profile_bio(self, db_session: AsyncSession, sample_user_with_profile):
        """Test updating profile bio"""
        # Arrange
        user, profile = sample_user_with_profile
        profile_service = ProfileService(db_session)
        new_bio = "Updated bio content for testing"

        update_data = FounderProfileUpdate(bio=new_bio)

        # Act
        updated_profile = await profile_service.update_profile(user.id, update_data)

        # Assert
        assert updated_profile is not None
        assert updated_profile.bio == new_bio
        assert updated_profile.user_id == user.id

    @pytest.mark.asyncio
    async def test_update_profile_current_focus(self, db_session: AsyncSession, sample_user_with_profile):
        """Test updating profile current focus"""
        # Arrange
        user, profile = sample_user_with_profile
        profile_service = ProfileService(db_session)
        new_focus = "Building AI-powered marketplace"

        update_data = FounderProfileUpdate(current_focus=new_focus)

        # Act
        updated_profile = await profile_service.update_profile(user.id, update_data)

        # Assert
        assert updated_profile.current_focus == new_focus

    @pytest.mark.asyncio
    async def test_update_profile_triggers_embedding_pipeline(
        self, db_session: AsyncSession, sample_user_with_profile
    ):
        """TDD: Profile update triggers embedding pipeline"""
        # Arrange
        user, profile = sample_user_with_profile
        profile_service = ProfileService(db_session)
        update_data = FounderProfileUpdate(
            bio="New bio content",
            current_focus="New focus area"
        )

        # Mock embedding service
        with patch('app.services.profile_service.EmbeddingService') as MockEmbedding:
            mock_embedding_instance = MockEmbedding.return_value
            mock_embedding_instance.create_profile_embedding = AsyncMock(
                return_value="embedding_id_123"
            )

            # Act
            await profile_service.update_profile(user.id, update_data)

        # Assert
        mock_embedding_instance.create_profile_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_profile_update_is_atomic(self, db_session: AsyncSession, sample_user_with_profile):
        """TDD: No partial updates allowed - updates are atomic"""
        # Arrange
        user, profile = sample_user_with_profile
        profile_service = ProfileService(db_session)

        original_bio = profile.bio
        original_focus = profile.current_focus

        update_data = FounderProfileUpdate(
            bio="New bio",
            current_focus="New focus"
        )

        # Mock embedding to raise exception
        with patch('app.services.profile_service.EmbeddingService') as MockEmbedding:
            mock_embedding_instance = MockEmbedding.return_value
            mock_embedding_instance.create_profile_embedding = AsyncMock(
                side_effect=Exception("Embedding failed")
            )

            # Act - Update should fail completely
            with pytest.raises(Exception):
                await profile_service.update_profile(user.id, update_data)

        # Assert - Profile should remain unchanged (rollback)
        await db_session.rollback()
        await db_session.refresh(profile)

        assert profile.bio == original_bio
        assert profile.current_focus == original_focus

    @pytest.mark.asyncio
    async def test_update_autonomy_mode(self, db_session: AsyncSession, sample_user_with_profile):
        """Test updating autonomy mode"""
        # Arrange
        user, profile = sample_user_with_profile
        profile_service = ProfileService(db_session)

        update_data = FounderProfileUpdate(autonomy_mode=AutonomyMode.AUTO)

        # Act
        updated_profile = await profile_service.update_profile(user.id, update_data)

        # Assert
        assert updated_profile.autonomy_mode == AutonomyMode.AUTO

    @pytest.mark.asyncio
    async def test_update_public_visibility(self, db_session: AsyncSession, sample_user_with_profile):
        """Test updating public visibility"""
        # Arrange
        user, profile = sample_user_with_profile
        profile_service = ProfileService(db_session)

        update_data = FounderProfileUpdate(public_visibility=False)

        # Act
        updated_profile = await profile_service.update_profile(user.id, update_data)

        # Assert
        assert updated_profile.public_visibility is False

    @pytest.mark.asyncio
    async def test_partial_update_only_changes_specified_fields(
        self, db_session: AsyncSession, sample_user_with_profile
    ):
        """Test partial update only changes specified fields"""
        # Arrange
        user, profile = sample_user_with_profile
        profile_service = ProfileService(db_session)

        original_bio = profile.bio
        original_autonomy = profile.autonomy_mode

        # Only update current_focus
        update_data = FounderProfileUpdate(current_focus="Only updating this field")

        # Act
        with patch('app.services.profile_service.EmbeddingService') as MockEmbedding:
            mock_embedding_instance = MockEmbedding.return_value
            mock_embedding_instance.create_profile_embedding = AsyncMock(
                return_value="embedding_id_456"
            )

            updated_profile = await profile_service.update_profile(user.id, update_data)

        # Assert
        assert updated_profile.current_focus == "Only updating this field"
        assert updated_profile.bio == original_bio  # Unchanged
        assert updated_profile.autonomy_mode == original_autonomy  # Unchanged

    @pytest.mark.asyncio
    async def test_update_profile_updates_timestamp(
        self, db_session: AsyncSession, sample_user_with_profile
    ):
        """Test updating profile updates the updated_at timestamp"""
        # Arrange
        user, profile = sample_user_with_profile
        profile_service = ProfileService(db_session)
        original_updated_at = profile.updated_at

        update_data = FounderProfileUpdate(bio="Updated bio")

        # Act
        with patch('app.services.profile_service.EmbeddingService') as MockEmbedding:
            mock_embedding_instance = MockEmbedding.return_value
            mock_embedding_instance.create_profile_embedding = AsyncMock()

            await profile_service.update_profile(user.id, update_data)

        # Assert
        await db_session.refresh(profile)
        assert profile.updated_at > original_updated_at


@pytest.mark.unit
class TestProfileVisibility:
    """Test suite for profile visibility"""

    @pytest.mark.asyncio
    async def test_get_public_profiles_only_returns_public(
        self, db_session: AsyncSession, sample_user_with_profile
    ):
        """Test retrieving only public profiles"""
        # Arrange
        user, profile = sample_user_with_profile
        profile_service = ProfileService(db_session)

        # Set profile to private
        profile.public_visibility = False
        await db_session.commit()

        # Act
        public_profiles = await profile_service.get_public_profiles(limit=10)

        # Assert
        # Should not include the private profile
        profile_ids = [p.user_id for p in public_profiles]
        assert user.id not in profile_ids

    @pytest.mark.asyncio
    async def test_can_view_own_private_profile(
        self, db_session: AsyncSession, sample_user_with_profile
    ):
        """Test user can view their own private profile"""
        # Arrange
        user, profile = sample_user_with_profile
        profile_service = ProfileService(db_session)

        # Set profile to private
        profile.public_visibility = False
        await db_session.commit()

        # Act
        retrieved_profile = await profile_service.get_profile(user.id)

        # Assert
        assert retrieved_profile is not None
        assert retrieved_profile.user_id == user.id
        assert retrieved_profile.public_visibility is False
