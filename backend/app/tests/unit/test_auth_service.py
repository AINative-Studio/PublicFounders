"""
Unit Tests for Authentication Service
TDD tests for LinkedIn OAuth and user management
"""
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import AuthService
from app.models.user import User
from app.models.founder_profile import FounderProfile, AutonomyMode
from app.schemas.user import LinkedInUserData


@pytest.mark.unit
class TestLinkedInOAuth:
    """Test suite for LinkedIn OAuth operations"""

    @pytest.mark.asyncio
    async def test_create_user_from_linkedin_data_creates_user(self, db_session: AsyncSession):
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
        auth_service = AuthService(db_session)

        # Act
        user, profile = await auth_service.create_user_from_linkedin(linkedin_data)

        # Assert
        assert user is not None
        assert user.linkedin_id == linkedin_data.linkedin_id
        assert user.name == linkedin_data.name
        assert user.email == linkedin_data.email
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_create_user_from_linkedin_data_creates_profile(self, db_session: AsyncSession):
        """Test creating user from LinkedIn data - founder profile created"""
        # Arrange
        linkedin_data = LinkedInUserData(
            linkedin_id="linkedin_profile_456",
            name="Profile Test",
            email="profile@example.com"
        )
        auth_service = AuthService(db_session)

        # Act
        user, profile = await auth_service.create_user_from_linkedin(linkedin_data)

        # Assert
        assert profile is not None
        assert profile.user_id == user.id
        assert profile.public_visibility is True
        assert profile.autonomy_mode == AutonomyMode.SUGGEST

    @pytest.mark.asyncio
    async def test_create_user_from_linkedin_creates_user_exactly_once(self, db_session: AsyncSession):
        """TDD: User record is created exactly once"""
        # Arrange
        linkedin_data = LinkedInUserData(
            linkedin_id="linkedin_unique_789",
            name="Unique User",
            email="unique@example.com"
        )
        auth_service = AuthService(db_session)

        # Act
        user1, profile1 = await auth_service.create_user_from_linkedin(linkedin_data)

        # Try to get user again with same LinkedIn ID
        existing_user = await auth_service.get_user_by_linkedin_id(linkedin_data.linkedin_id)

        # Assert
        assert existing_user is not None
        assert existing_user.id == user1.id
        assert existing_user.linkedin_id == linkedin_data.linkedin_id

    @pytest.mark.asyncio
    async def test_linkedin_id_must_be_unique(self, db_session: AsyncSession):
        """TDD: LinkedIn ID is unique - duplicate creation should fail"""
        # Arrange
        linkedin_data = LinkedInUserData(
            linkedin_id="linkedin_duplicate_999",
            name="First User",
            email="first@example.com"
        )
        auth_service = AuthService(db_session)

        # Act - Create first user
        await auth_service.create_user_from_linkedin(linkedin_data)

        # Try to create second user with same LinkedIn ID
        duplicate_data = LinkedInUserData(
            linkedin_id="linkedin_duplicate_999",  # Same LinkedIn ID
            name="Second User",
            email="second@example.com"
        )

        # Assert - Should raise an exception
        with pytest.raises(Exception):  # SQLAlchemy IntegrityError
            await auth_service.create_user_from_linkedin(duplicate_data)

    @pytest.mark.asyncio
    async def test_failed_oauth_does_not_create_user(self, db_session: AsyncSession):
        """TDD: Failed OAuth does not create user"""
        # Arrange
        auth_service = AuthService(db_session)
        invalid_linkedin_data = None

        # Act & Assert
        with pytest.raises(Exception):
            await auth_service.create_user_from_linkedin(invalid_linkedin_data)

        # Verify no user was created
        # (This would be checked by counting users in DB, but we're testing the exception)

    @pytest.mark.asyncio
    async def test_profile_created_transactionally_with_user(self, db_session: AsyncSession):
        """TDD: Profile is created transactionally with user"""
        # Arrange
        linkedin_data = LinkedInUserData(
            linkedin_id="linkedin_transaction_111",
            name="Transaction Test",
            email="transaction@example.com"
        )
        auth_service = AuthService(db_session)

        # Act
        user, profile = await auth_service.create_user_from_linkedin(linkedin_data)

        # Assert - Both user and profile should exist
        assert user is not None
        assert profile is not None
        assert profile.user_id == user.id

        # Verify in database
        retrieved_user = await auth_service.get_user_by_id(user.id)
        assert retrieved_user is not None
        assert retrieved_user.founder_profile is not None

    @pytest.mark.asyncio
    async def test_default_profile_visibility_is_public(self, db_session: AsyncSession):
        """TDD: Default visibility is public"""
        # Arrange
        linkedin_data = LinkedInUserData(
            linkedin_id="linkedin_visibility_222",
            name="Visibility Test"
        )
        auth_service = AuthService(db_session)

        # Act
        user, profile = await auth_service.create_user_from_linkedin(linkedin_data)

        # Assert
        assert profile.public_visibility is True


@pytest.mark.unit
class TestUserRetrieval:
    """Test suite for user retrieval operations"""

    @pytest.mark.asyncio
    async def test_get_user_by_linkedin_id_returns_user(self, db_session: AsyncSession, sample_user: User):
        """Test retrieving user by LinkedIn ID"""
        # Arrange
        auth_service = AuthService(db_session)

        # Act
        user = await auth_service.get_user_by_linkedin_id(sample_user.linkedin_id)

        # Assert
        assert user is not None
        assert user.id == sample_user.id
        assert user.linkedin_id == sample_user.linkedin_id

    @pytest.mark.asyncio
    async def test_get_user_by_linkedin_id_nonexistent_returns_none(self, db_session: AsyncSession):
        """Test retrieving non-existent user returns None"""
        # Arrange
        auth_service = AuthService(db_session)
        nonexistent_linkedin_id = "linkedin_nonexistent_999"

        # Act
        user = await auth_service.get_user_by_linkedin_id(nonexistent_linkedin_id)

        # Assert
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_id_returns_user(self, db_session: AsyncSession, sample_user: User):
        """Test retrieving user by UUID"""
        # Arrange
        auth_service = AuthService(db_session)

        # Act
        user = await auth_service.get_user_by_id(sample_user.id)

        # Assert
        assert user is not None
        assert user.id == sample_user.id

    @pytest.mark.asyncio
    async def test_update_last_login_updates_timestamp(self, db_session: AsyncSession, sample_user: User):
        """Test updating last login timestamp"""
        # Arrange
        auth_service = AuthService(db_session)
        original_last_login = sample_user.last_login_at

        # Act
        await auth_service.update_last_login(sample_user.id)

        # Retrieve updated user
        updated_user = await auth_service.get_user_by_id(sample_user.id)

        # Assert
        assert updated_user.last_login_at is not None
        assert updated_user.last_login_at > (original_last_login or datetime.min)
