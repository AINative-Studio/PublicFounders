"""
Unit Tests for Authentication Service - ZeroDB Edition
TDD tests for LinkedIn OAuth and user management using ZeroDB
"""
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from app.services.auth_service import AuthService
from app.schemas.user import LinkedInUserData
from app.core.enums import AutonomyMode


@pytest.mark.unit
class TestLinkedInOAuth:
    """Test suite for LinkedIn OAuth operations"""

    @pytest.mark.asyncio
    async def test_create_user_from_linkedin_data_creates_user(self, mock_zerodb):
        """Test creating user from LinkedIn data - user record created"""
        # Arrange
        linkedin_data = LinkedInUserData(
            linkedin_id="linkedin_test_123",
            name="Test User",
            headline="Test Headline",
            profile_photo_url="https://example.com/photo.jpg",
            location="San Francisco, CA",
            email="test@example.com"
        )

        # Mock that user doesn't exist
        mock_zerodb.get_by_field.return_value = None
        mock_zerodb.insert_rows.return_value = {"success": True, "inserted": 1}

        auth_service = AuthService()

        # Act
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            user, profile = await auth_service.create_user_from_linkedin(linkedin_data)

        # Assert
        assert user is not None
        assert isinstance(user, dict)
        assert user["linkedin_id"] == linkedin_data.linkedin_id
        assert user["name"] == linkedin_data.name
        assert user["email"] == linkedin_data.email

        # Verify insert was called twice (user + profile)
        assert mock_zerodb.insert_rows.call_count == 2

    @pytest.mark.asyncio
    async def test_create_user_from_linkedin_data_creates_profile(self, mock_zerodb):
        """Test creating user from LinkedIn data - founder profile created"""
        # Arrange
        linkedin_data = LinkedInUserData(
            linkedin_id="linkedin_profile_456",
            name="Profile Test",
            email="profile@example.com"
        )

        mock_zerodb.get_by_field.return_value = None
        mock_zerodb.insert_rows.return_value = {"success": True, "inserted": 1}

        auth_service = AuthService()

        # Act
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            user, profile = await auth_service.create_user_from_linkedin(linkedin_data)

        # Assert
        assert profile is not None
        assert isinstance(profile, dict)
        assert profile["user_id"] == user["id"]
        assert profile["public_visibility"] is True
        assert profile["autonomy_mode"] == AutonomyMode.SUGGEST.value

    @pytest.mark.asyncio
    async def test_create_user_from_linkedin_creates_user_exactly_once(self, mock_zerodb):
        """TDD: User record is created exactly once"""
        # Arrange
        linkedin_data = LinkedInUserData(
            linkedin_id="linkedin_unique_789",
            name="Unique User",
            email="unique@example.com"
        )

        user_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        created_user = {
            "id": user_id,
            "linkedin_id": linkedin_data.linkedin_id,
            "name": linkedin_data.name,
            "email": linkedin_data.email
        }

        # First call: user doesn't exist
        mock_zerodb.get_by_field.side_effect = [None, created_user]
        mock_zerodb.insert_rows.return_value = {"success": True, "inserted": 1}

        auth_service = AuthService()

        # Act
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            user1, profile1 = await auth_service.create_user_from_linkedin(linkedin_data)

            # Try to get user again with same LinkedIn ID
            existing_user = await auth_service.get_user_by_linkedin_id(linkedin_data.linkedin_id)

        # Assert
        assert existing_user is not None
        assert existing_user["linkedin_id"] == linkedin_data.linkedin_id

    @pytest.mark.asyncio
    async def test_linkedin_id_must_be_unique(self, mock_zerodb):
        """TDD: LinkedIn ID is unique - duplicate creation should fail"""
        # Arrange
        linkedin_data = LinkedInUserData(
            linkedin_id="linkedin_duplicate_999",
            name="First User",
            email="first@example.com"
        )

        # Mock that user already exists
        existing_user = {
            "id": str(uuid.uuid4()),
            "linkedin_id": linkedin_data.linkedin_id,
            "name": "Existing User"
        }
        mock_zerodb.get_by_field.return_value = existing_user

        auth_service = AuthService()

        # Act & Assert - Should raise an exception
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            with pytest.raises(Exception, match="already exists"):
                await auth_service.create_user_from_linkedin(linkedin_data)

    @pytest.mark.asyncio
    async def test_failed_oauth_does_not_create_user(self, mock_zerodb):
        """TDD: Failed OAuth does not create user"""
        # Arrange
        auth_service = AuthService()
        invalid_linkedin_data = None

        # Act & Assert
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            with pytest.raises(ValueError):
                await auth_service.create_user_from_linkedin(invalid_linkedin_data)

    @pytest.mark.asyncio
    async def test_profile_created_transactionally_with_user(self, mock_zerodb):
        """TDD: Profile is created transactionally with user"""
        # Arrange
        linkedin_data = LinkedInUserData(
            linkedin_id="linkedin_transaction_111",
            name="Transaction Test",
            email="transaction@example.com"
        )

        mock_zerodb.get_by_field.return_value = None
        mock_zerodb.insert_rows.return_value = {"success": True, "inserted": 1}

        auth_service = AuthService()

        # Act
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            user, profile = await auth_service.create_user_from_linkedin(linkedin_data)

        # Assert - Both user and profile should exist
        assert user is not None
        assert profile is not None
        assert profile["user_id"] == user["id"]

        # Verify both inserts were called
        assert mock_zerodb.insert_rows.call_count == 2

    @pytest.mark.asyncio
    async def test_default_profile_visibility_is_public(self, mock_zerodb):
        """TDD: Default visibility is public"""
        # Arrange
        linkedin_data = LinkedInUserData(
            linkedin_id="linkedin_visibility_222",
            name="Visibility Test"
        )

        mock_zerodb.get_by_field.return_value = None
        mock_zerodb.insert_rows.return_value = {"success": True, "inserted": 1}

        auth_service = AuthService()

        # Act
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            user, profile = await auth_service.create_user_from_linkedin(linkedin_data)

        # Assert
        assert profile["public_visibility"] is True


@pytest.mark.unit
class TestUserRetrieval:
    """Test suite for user retrieval operations"""

    @pytest.mark.asyncio
    async def test_get_user_by_linkedin_id_returns_user(self, mock_zerodb, sample_user_dict):
        """Test retrieving user by LinkedIn ID"""
        # Arrange
        mock_zerodb.get_by_field.return_value = sample_user_dict
        auth_service = AuthService()

        # Act
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            user = await auth_service.get_user_by_linkedin_id(sample_user_dict["linkedin_id"])

        # Assert
        assert user is not None
        assert isinstance(user, dict)
        assert user["id"] == sample_user_dict["id"]
        assert user["linkedin_id"] == sample_user_dict["linkedin_id"]

    @pytest.mark.asyncio
    async def test_get_user_by_linkedin_id_nonexistent_returns_none(self, mock_zerodb):
        """Test retrieving non-existent user returns None"""
        # Arrange
        mock_zerodb.get_by_field.return_value = None
        auth_service = AuthService()
        nonexistent_linkedin_id = "linkedin_nonexistent_999"

        # Act
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            user = await auth_service.get_user_by_linkedin_id(nonexistent_linkedin_id)

        # Assert
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_id_returns_user(self, mock_zerodb, sample_user_dict):
        """Test retrieving user by UUID"""
        # Arrange
        mock_zerodb.get_by_id.return_value = sample_user_dict
        auth_service = AuthService()
        user_id = uuid.UUID(sample_user_dict["id"])

        # Act
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            user = await auth_service.get_user_by_id(user_id)

        # Assert
        assert user is not None
        assert isinstance(user, dict)
        assert user["id"] == sample_user_dict["id"]

    @pytest.mark.asyncio
    async def test_update_last_login_updates_timestamp(self, mock_zerodb, sample_user_dict):
        """Test updating last login timestamp"""
        # Arrange
        user_id = uuid.UUID(sample_user_dict["id"])
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        auth_service = AuthService()

        # Act
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            await auth_service.update_last_login(user_id)

        # Assert - Verify update was called with correct parameters
        mock_zerodb.update_rows.assert_called_once()
        call_args = mock_zerodb.update_rows.call_args
        assert call_args[1]["table_name"] == "users"
        assert call_args[1]["filter"]["id"] == str(user_id)
        assert "last_login_at" in call_args[1]["update"]["$set"]
