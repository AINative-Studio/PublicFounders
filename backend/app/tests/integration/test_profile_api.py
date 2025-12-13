"""
Integration Tests for Profile API
Tests for founder profile CRUD endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.founder_profile import FounderProfile, AutonomyMode
from app.core.security import create_access_token


@pytest.mark.integration
class TestGetMyProfile:
    """Integration tests for GET /profile/me"""

    @pytest.mark.asyncio
    async def test_get_my_profile_success(
        self,
        client: AsyncClient,
        sample_user_with_profile
    ):
        """Test getting current user's profile with valid token"""
        # Arrange
        user, profile = sample_user_with_profile
        token = create_access_token({"sub": str(user.id), "linkedin_id": user.linkedin_id})

        # Act
        response = await client.get(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert "user" in data
        assert "profile" in data
        assert data["user"]["id"] == str(user.id)
        assert data["profile"]["user_id"] == str(user.id)

    @pytest.mark.asyncio
    async def test_get_my_profile_unauthorized(self, client: AsyncClient):
        """Test getting profile without authentication fails"""
        # Act
        response = await client.get("/api/v1/profile/me")

        # Assert
        assert response.status_code == 403  # Forbidden (no auth header)

    @pytest.mark.asyncio
    async def test_get_my_profile_invalid_token(self, client: AsyncClient):
        """Test getting profile with invalid token fails"""
        # Act
        response = await client.get(
            "/api/v1/profile/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )

        # Assert
        assert response.status_code == 401  # Unauthorized


@pytest.mark.integration
class TestUpdateMyProfile:
    """Integration tests for PUT /profile/me"""

    @pytest.mark.asyncio
    async def test_update_profile_bio(
        self,
        client: AsyncClient,
        sample_user_with_profile
    ):
        """Test updating profile bio"""
        # Arrange
        user, profile = sample_user_with_profile
        token = create_access_token({"sub": str(user.id), "linkedin_id": user.linkedin_id})

        new_bio = "Updated bio for testing purposes"

        # Act
        response = await client.put(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"bio": new_bio}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["bio"] == new_bio
        assert data["user_id"] == str(user.id)

    @pytest.mark.asyncio
    async def test_update_profile_current_focus(
        self,
        client: AsyncClient,
        sample_user_with_profile
    ):
        """Test updating current focus"""
        # Arrange
        user, profile = sample_user_with_profile
        token = create_access_token({"sub": str(user.id), "linkedin_id": user.linkedin_id})

        new_focus = "Building next-generation AI platform"

        # Act
        response = await client.put(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_focus": new_focus}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["current_focus"] == new_focus

    @pytest.mark.asyncio
    async def test_update_profile_autonomy_mode(
        self,
        client: AsyncClient,
        sample_user_with_profile
    ):
        """Test updating autonomy mode"""
        # Arrange
        user, profile = sample_user_with_profile
        token = create_access_token({"sub": str(user.id), "linkedin_id": user.linkedin_id})

        # Act
        response = await client.put(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"autonomy_mode": "auto"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["autonomy_mode"] == "auto"

    @pytest.mark.asyncio
    async def test_update_profile_visibility(
        self,
        client: AsyncClient,
        sample_user_with_profile
    ):
        """Test updating profile visibility"""
        # Arrange
        user, profile = sample_user_with_profile
        token = create_access_token({"sub": str(user.id), "linkedin_id": user.linkedin_id})

        # Act
        response = await client.put(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"public_visibility": False}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["public_visibility"] is False

    @pytest.mark.asyncio
    async def test_update_profile_unauthorized(self, client: AsyncClient):
        """Test updating profile without auth fails"""
        # Act
        response = await client.put(
            "/api/v1/profile/me",
            json={"bio": "Should fail"}
        )

        # Assert
        assert response.status_code == 403  # Forbidden


@pytest.mark.integration
class TestGetUserProfile:
    """Integration tests for GET /profile/{user_id}"""

    @pytest.mark.asyncio
    async def test_get_public_profile(
        self,
        client: AsyncClient,
        sample_user_with_profile
    ):
        """Test getting another user's public profile"""
        # Arrange
        user, profile = sample_user_with_profile

        # Ensure profile is public
        assert profile.public_visibility is True

        # Act
        response = await client.get(f"/api/v1/profile/{user.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["user"]["id"] == str(user.id)
        assert data["profile"]["public_visibility"] is True

    @pytest.mark.asyncio
    async def test_get_private_profile_forbidden(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_user_with_profile
    ):
        """Test getting private profile returns 403"""
        # Arrange
        user, profile = sample_user_with_profile

        # Make profile private
        profile.public_visibility = False
        await db_session.commit()

        # Act
        response = await client.get(f"/api/v1/profile/{user.id}")

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_nonexistent_profile(self, client: AsyncClient):
        """Test getting non-existent profile returns 404"""
        # Arrange
        import uuid
        nonexistent_id = uuid.uuid4()

        # Act
        response = await client.get(f"/api/v1/profile/{nonexistent_id}")

        # Assert
        assert response.status_code == 404


@pytest.mark.integration
class TestListPublicProfiles:
    """Integration tests for GET /profile/"""

    @pytest.mark.asyncio
    async def test_list_public_profiles(
        self,
        client: AsyncClient,
        sample_user_with_profile
    ):
        """Test listing public profiles"""
        # Act
        response = await client.get("/api/v1/profile/")

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 1

        # Check structure
        if len(data) > 0:
            assert "user" in data[0]
            assert "profile" in data[0]

    @pytest.mark.asyncio
    async def test_list_public_profiles_pagination(
        self,
        client: AsyncClient,
        sample_user_with_profile
    ):
        """Test pagination parameters"""
        # Act
        response = await client.get(
            "/api/v1/profile/",
            params={"limit": 5, "offset": 0}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) <= 5

    @pytest.mark.asyncio
    async def test_list_profiles_excludes_private(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_user_with_profile
    ):
        """Test listing profiles excludes private ones"""
        # Arrange
        user, profile = sample_user_with_profile

        # Make profile private
        profile.public_visibility = False
        await db_session.commit()

        # Act
        response = await client.get("/api/v1/profile/")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Private profile should not be in list
        profile_ids = [p["user"]["id"] for p in data]
        assert str(user.id) not in profile_ids
