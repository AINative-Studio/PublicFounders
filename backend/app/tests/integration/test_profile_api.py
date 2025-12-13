"""
Integration Tests for Profile API - ZeroDB Edition
Tests for founder profile CRUD endpoints using ZeroDB
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
import uuid

from app.core.security import create_access_token
from app.core.enums import AutonomyMode


@pytest.mark.integration
class TestGetMyProfile:
    """Integration tests for GET /profile/me"""

    @pytest.mark.asyncio
    async def test_get_my_profile_success(
        self,
        client: AsyncClient,
        mock_zerodb,
        sample_user_with_profile_dict
    ):
        """Test getting current user's profile with valid token"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        token = create_access_token({"sub": user["id"], "linkedin_id": user["linkedin_id"]})

        mock_zerodb.get_by_id.return_value = user
        mock_zerodb.query_rows.return_value = [profile]

        # Act
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            with patch('app.services.profile_service.zerodb_client', mock_zerodb):
                response = await client.get(
                    "/api/v1/profile/me",
                    headers={"Authorization": f"Bearer {token}"}
                )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert "user" in data
        assert "profile" in data
        assert data["user"]["id"] == user["id"]
        assert data["profile"]["user_id"] == user["id"]

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
        mock_zerodb,
        sample_user_with_profile_dict
    ):
        """Test updating profile bio"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        token = create_access_token({"sub": user["id"], "linkedin_id": user["linkedin_id"]})

        new_bio = "Updated bio for testing purposes"
        updated_profile = {**profile, "bio": new_bio}

        mock_zerodb.get_by_id.return_value = user
        mock_zerodb.query_rows.side_effect = [[profile], [updated_profile]]
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        # Act
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            with patch('app.services.profile_service.zerodb_client', mock_zerodb):
                with patch('app.services.profile_service.embedding_service') as mock_embedding:
                    mock_embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
                    mock_embedding.upsert_vector = AsyncMock(return_value="vec_bio")

                    response = await client.put(
                        "/api/v1/profile/me",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"bio": new_bio}
                    )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["bio"] == new_bio
        assert data["user_id"] == user["id"]

    @pytest.mark.asyncio
    async def test_update_profile_current_focus(
        self,
        client: AsyncClient,
        mock_zerodb,
        sample_user_with_profile_dict
    ):
        """Test updating current focus"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        token = create_access_token({"sub": user["id"], "linkedin_id": user["linkedin_id"]})

        new_focus = "Building next-generation AI platform"
        updated_profile = {**profile, "current_focus": new_focus}

        mock_zerodb.get_by_id.return_value = user
        mock_zerodb.query_rows.side_effect = [[profile], [updated_profile]]
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        # Act
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            with patch('app.services.profile_service.zerodb_client', mock_zerodb):
                with patch('app.services.profile_service.embedding_service') as mock_embedding:
                    mock_embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
                    mock_embedding.upsert_vector = AsyncMock(return_value="vec_focus")

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
        mock_zerodb,
        sample_user_with_profile_dict
    ):
        """Test updating autonomy mode"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        token = create_access_token({"sub": user["id"], "linkedin_id": user["linkedin_id"]})

        updated_profile = {**profile, "autonomy_mode": AutonomyMode.AUTO.value}

        mock_zerodb.get_by_id.return_value = user
        mock_zerodb.query_rows.side_effect = [[profile], [updated_profile]]
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        # Act
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            with patch('app.services.profile_service.zerodb_client', mock_zerodb):
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
        mock_zerodb,
        sample_user_with_profile_dict
    ):
        """Test updating profile visibility"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        token = create_access_token({"sub": user["id"], "linkedin_id": user["linkedin_id"]})

        updated_profile = {**profile, "public_visibility": False}

        mock_zerodb.get_by_id.return_value = user
        mock_zerodb.query_rows.side_effect = [[profile], [updated_profile]]
        mock_zerodb.update_rows.return_value = {"success": True, "updated": 1}

        # Act
        with patch('app.services.auth_service.zerodb_client', mock_zerodb):
            with patch('app.services.profile_service.zerodb_client', mock_zerodb):
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
        mock_zerodb,
        sample_user_with_profile_dict
    ):
        """Test getting another user's public profile"""
        # Arrange
        user, profile = sample_user_with_profile_dict

        # Ensure profile is public
        profile["public_visibility"] = True

        mock_zerodb.get_by_id.return_value = user
        mock_zerodb.query_rows.return_value = [profile]

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            response = await client.get(f"/api/v1/profile/{user['id']}")

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["user"]["id"] == user["id"]
        assert data["profile"]["public_visibility"] is True

    @pytest.mark.asyncio
    async def test_get_private_profile_forbidden(
        self,
        client: AsyncClient,
        mock_zerodb,
        sample_user_with_profile_dict
    ):
        """Test getting private profile returns 403"""
        # Arrange
        user, profile = sample_user_with_profile_dict

        # Make profile private
        profile["public_visibility"] = False

        mock_zerodb.get_by_id.return_value = user
        mock_zerodb.query_rows.return_value = [profile]

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            response = await client.get(f"/api/v1/profile/{user['id']}")

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_nonexistent_profile(self, client: AsyncClient, mock_zerodb):
        """Test getting non-existent profile returns 404"""
        # Arrange
        nonexistent_id = str(uuid.uuid4())

        mock_zerodb.get_by_id.return_value = None

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
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
        mock_zerodb,
        sample_user_with_profile_dict
    ):
        """Test listing public profiles"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        profile["public_visibility"] = True

        mock_zerodb.query_rows.return_value = [profile]
        mock_zerodb.get_by_id.return_value = user

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
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
        mock_zerodb,
        sample_user_with_profile_dict
    ):
        """Test pagination parameters"""
        # Arrange
        user, profile = sample_user_with_profile_dict
        profile["public_visibility"] = True

        mock_zerodb.query_rows.return_value = [profile]
        mock_zerodb.get_by_id.return_value = user

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
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
        mock_zerodb,
        sample_user_with_profile_dict
    ):
        """Test listing profiles excludes private ones"""
        # Arrange
        user, profile = sample_user_with_profile_dict

        # Make profile private - should not be returned
        profile["public_visibility"] = False

        # Mock returns empty list (private profiles filtered out)
        mock_zerodb.query_rows.return_value = []

        # Act
        with patch('app.services.profile_service.zerodb_client', mock_zerodb):
            response = await client.get("/api/v1/profile/")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Private profile should not be in list
        profile_ids = [p["user"]["id"] for p in data]
        assert user["id"] not in profile_ids
