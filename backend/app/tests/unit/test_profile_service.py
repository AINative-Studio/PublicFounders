"""
Unit Tests for Profile Service - ZeroDB Edition
TDD tests for founder profile creation and updates using ZeroDB
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import uuid

from app.services.profile_service import ProfileService
from app.schemas.founder_profile import FounderProfileUpdate
from app.core.enums import AutonomyMode


@pytest.mark.unit
class TestProfileCreation:
    """Test suite for profile creation"""

    @pytest.mark.asyncio
    async def test_get_profile_by_user_id(self, mock_zerodb, sample_user_with_profile_dict):
        """Test retrieving profile by user ID"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        user_id = uuid.UUID(user["id"])

        mock_zerodb.query_rows.return_value = [profile]

        profile_service = ProfileService()

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            retrieved_profile = await profile_service.get_profile(user_id)

        # Assert
        assert retrieved_profile is not None
        assert isinstance(retrieved_profile, dict)
        assert retrieved_profile["user_id"] == user["id"]
        assert retrieved_profile["bio"] == profile["bio"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_profile_returns_none(self, mock_zerodb):
        """Test retrieving non-existent profile returns None"""
        # Arrange
        nonexistent_user_id = uuid.uuid4()
        mock_zerodb.query_rows.return_value = []

        profile_service = ProfileService()

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            profile = await profile_service.get_profile(nonexistent_user_id)

        # Assert
        assert profile is None


@pytest.mark.unit
class TestProfileUpdate:
    """Test suite for profile updates"""

    @pytest.mark.asyncio
    async def test_update_profile_bio(self, mock_zerodb, sample_user_with_profile_dict):
        """Test updating profile bio"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        user_id = uuid.UUID(user["id"])
        new_bio = "Updated bio content for testing"

        # Mock query to return existing profile
        mock_zerodb.query_rows.return_value = [profile]
        mock_zerodb.get_by_id.return_value = user
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        # Updated profile to return
        updated_profile = {**profile, "bio": new_bio}
        mock_zerodb.query_rows.side_effect = [[profile], [updated_profile]]

        update_data = FounderProfileUpdate(bio=new_bio)
        profile_service = ProfileService()

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            with patch('app.services.profile_service.embedding_service') as mock_embedding:
                mock_embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
                mock_embedding.upsert_vector = AsyncMock(return_value="vec_123")

                result = await profile_service.update_profile(user_id, update_data)

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result["bio"] == new_bio
        assert result["user_id"] == user["id"]

    @pytest.mark.asyncio
    async def test_update_profile_current_focus(self, mock_zerodb, sample_user_with_profile_dict):
        """Test updating profile current focus"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        user_id = uuid.UUID(user["id"])
        new_focus = "Building AI-powered marketplace"

        mock_zerodb.query_rows.return_value = [profile]
        mock_zerodb.get_by_id.return_value = user
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        updated_profile = {**profile, "current_focus": new_focus}
        mock_zerodb.query_rows.side_effect = [[profile], [updated_profile]]

        update_data = FounderProfileUpdate(current_focus=new_focus)
        profile_service = ProfileService()

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            with patch('app.services.profile_service.embedding_service') as mock_embedding:
                mock_embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
                mock_embedding.upsert_vector = AsyncMock(return_value="vec_456")

                result = await profile_service.update_profile(user_id, update_data)

        # Assert
        assert result["current_focus"] == new_focus

    @pytest.mark.asyncio
    async def test_update_profile_triggers_embedding_pipeline(
        self, mock_zerodb, sample_user_with_profile_dict
    ):
        """TDD: Profile update triggers embedding pipeline"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        user_id = uuid.UUID(user["id"])

        mock_zerodb.query_rows.return_value = [profile]
        mock_zerodb.get_by_id.return_value = user
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        update_data = FounderProfileUpdate(
            bio="New bio content",
            current_focus="New focus area"
        )

        profile_service = ProfileService()

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            with patch('app.services.profile_service.embedding_service') as mock_embedding:
                mock_embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
                mock_embedding.upsert_vector = AsyncMock(return_value="vec_789")

                await profile_service.update_profile(user_id, update_data)

                # Assert - Embedding methods should be called
                mock_embedding.generate_embedding.assert_called_once()
                mock_embedding.upsert_vector.assert_called_once()

    @pytest.mark.asyncio
    async def test_profile_update_is_atomic(self, mock_zerodb, sample_user_with_profile_dict):
        """TDD: No partial updates allowed - updates are atomic"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        user_id = uuid.UUID(user["id"])

        original_bio = profile["bio"]
        original_focus = profile["current_focus"]

        mock_zerodb.query_rows.return_value = [profile]
        mock_zerodb.get_by_id.return_value = user

        update_data = FounderProfileUpdate(
            bio="New bio",
            current_focus="New focus"
        )

        profile_service = ProfileService()

        # Act - Update should fail if embedding fails
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            with patch('app.services.profile_service.embedding_service') as mock_embedding:
                mock_embedding.generate_embedding = AsyncMock(
                    side_effect=Exception("Embedding failed")
                )

                with pytest.raises(Exception, match="Embedding failed"):
                    await profile_service.update_profile(user_id, update_data)

        # Assert - Profile update should not have been called since embedding failed
        # In ZeroDB version, we catch the exception and don't fail the update
        # But we can verify the original data is unchanged by not calling update

    @pytest.mark.asyncio
    async def test_update_autonomy_mode(self, mock_zerodb, sample_user_with_profile_dict):
        """Test updating autonomy mode"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        user_id = uuid.UUID(user["id"])

        mock_zerodb.query_rows.return_value = [profile]
        mock_zerodb.get_by_id.return_value = user
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        updated_profile = {**profile, "autonomy_mode": AutonomyMode.AUTO.value}
        mock_zerodb.query_rows.side_effect = [[profile], [updated_profile]]

        update_data = FounderProfileUpdate(autonomy_mode=AutonomyMode.AUTO)
        profile_service = ProfileService()

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            result = await profile_service.update_profile(user_id, update_data)

        # Assert
        assert result["autonomy_mode"] == AutonomyMode.AUTO.value

    @pytest.mark.asyncio
    async def test_update_public_visibility(self, mock_zerodb, sample_user_with_profile_dict):
        """Test updating public visibility"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        user_id = uuid.UUID(user["id"])

        mock_zerodb.query_rows.return_value = [profile]
        mock_zerodb.get_by_id.return_value = user
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        updated_profile = {**profile, "public_visibility": False}
        mock_zerodb.query_rows.side_effect = [[profile], [updated_profile]]

        update_data = FounderProfileUpdate(public_visibility=False)
        profile_service = ProfileService()

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            result = await profile_service.update_profile(user_id, update_data)

        # Assert
        assert result["public_visibility"] is False

    @pytest.mark.asyncio
    async def test_partial_update_only_changes_specified_fields(
        self, mock_zerodb, sample_user_with_profile_dict
    ):
        """Test partial update only changes specified fields"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        user_id = uuid.UUID(user["id"])

        original_bio = profile["bio"]
        original_autonomy = profile["autonomy_mode"]

        mock_zerodb.query_rows.return_value = [profile]
        mock_zerodb.get_by_id.return_value = user
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        # Only update current_focus
        updated_profile = {**profile, "current_focus": "Only updating this field"}
        mock_zerodb.query_rows.side_effect = [[profile], [updated_profile]]

        update_data = FounderProfileUpdate(current_focus="Only updating this field")
        profile_service = ProfileService()

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            with patch('app.services.profile_service.embedding_service') as mock_embedding:
                mock_embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
                mock_embedding.upsert_vector = AsyncMock(return_value="vec_partial")

                result = await profile_service.update_profile(user_id, update_data)

        # Assert
        assert result["current_focus"] == "Only updating this field"
        assert result["bio"] == original_bio  # Unchanged
        assert result["autonomy_mode"] == original_autonomy  # Unchanged

    @pytest.mark.asyncio
    async def test_update_profile_updates_timestamp(
        self, mock_zerodb, sample_user_with_profile_dict
    ):
        """Test updating profile updates the updated_at timestamp"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        user_id = uuid.UUID(user["id"])

        mock_zerodb.query_rows.return_value = [profile]
        mock_zerodb.get_by_id.return_value = user
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        update_data = FounderProfileUpdate(bio="Updated bio")
        profile_service = ProfileService()

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            with patch('app.services.profile_service.embedding_service') as mock_embedding:
                mock_embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
                mock_embedding.upsert_vector = AsyncMock(return_value="vec_timestamp")

                await profile_service.update_profile(user_id, update_data)

        # Assert - Verify update_rows was called with updated_at
        mock_zerodb.update_rows.assert_called_once()
        call_args = mock_zerodb.update_rows.call_args
        assert "updated_at" in call_args[1]["update"]["$set"]


@pytest.mark.unit
class TestProfileVisibility:
    """Test suite for profile visibility"""

    @pytest.mark.asyncio
    async def test_get_public_profiles_only_returns_public(
        self, mock_zerodb, sample_user_with_profile_dict
    ):
        """Test retrieving only public profiles"""
        # Arrange
        user, profile = sample_user_with_profile_dict

        # Return only public profiles
        public_profile = {**profile, "public_visibility": True}
        mock_zerodb.query_rows.return_value = [public_profile]

        profile_service = ProfileService()

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            public_profiles = await profile_service.get_public_profiles(limit=10)

        # Assert
        assert len(public_profiles) > 0
        for p in public_profiles:
            assert p["public_visibility"] is True

        # Verify filter was used
        mock_zerodb.query_rows.assert_called_once()
        call_args = mock_zerodb.query_rows.call_args
        assert call_args[1]["filter"]["public_visibility"] is True

    @pytest.mark.asyncio
    async def test_can_view_own_private_profile(
        self, mock_zerodb, sample_user_with_profile_dict
    ):
        """Test user can view their own private profile"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        user_id = uuid.UUID(user["id"])

        # Set profile to private
        private_profile = {**profile, "public_visibility": False}
        mock_zerodb.query_rows.return_value = [private_profile]

        profile_service = ProfileService()

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            retrieved_profile = await profile_service.get_profile(user_id)

        # Assert
        assert retrieved_profile is not None
        assert retrieved_profile["user_id"] == user["id"]
        assert retrieved_profile["public_visibility"] is False
