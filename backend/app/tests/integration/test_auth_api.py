"""
Integration Tests for Authentication API
Tests for LinkedIn OAuth and phone verification endpoints
"""
import pytest
from unittest.mock import patch, AsyncMock, Mock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@pytest.mark.integration
class TestLinkedInOAuth:
    """Integration tests for LinkedIn OAuth endpoints"""

    @pytest.mark.asyncio
    async def test_initiate_linkedin_oauth_redirects(self, client: AsyncClient):
        """Test LinkedIn OAuth initiate endpoint returns redirect URL"""
        # Act
        response = await client.get("/api/v1/auth/linkedin/initiate", follow_redirects=False)

        # Assert
        assert response.status_code in [200, 307, 302]  # Allow various redirect codes
        # Response should contain redirect or authorization URL

    @pytest.mark.asyncio
    async def test_linkedin_callback_creates_new_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        linkedin_user_data: dict
    ):
        """Test LinkedIn OAuth callback creates new user"""
        # Arrange
        mock_linkedin_token = {"access_token": "mock_token_123"}

        # Mock LinkedIn API calls
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                # Mock token exchange
                mock_post.return_value = Mock(
                    status_code=200,
                    json=lambda: mock_linkedin_token
                )

                # Mock user info
                mock_get.return_value = Mock(
                    status_code=200,
                    json=lambda: linkedin_user_data
                )

                # Act
                response = await client.get(
                    "/api/v1/auth/linkedin/callback",
                    params={"code": "mock_auth_code"}
                )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["linkedin_id"] == linkedin_user_data["sub"]
        assert data["created"] is True  # New user created

    @pytest.mark.asyncio
    async def test_linkedin_callback_returns_existing_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_user: User,
        linkedin_user_data: dict
    ):
        """Test LinkedIn OAuth callback returns existing user"""
        # Arrange
        # Update mock data to match existing user
        linkedin_user_data["sub"] = sample_user.linkedin_id

        mock_linkedin_token = {"access_token": "mock_token_456"}

        # Mock LinkedIn API calls
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_post.return_value = Mock(
                    status_code=200,
                    json=lambda: mock_linkedin_token
                )

                mock_get.return_value = Mock(
                    status_code=200,
                    json=lambda: linkedin_user_data
                )

                # Act
                response = await client.get(
                    "/api/v1/auth/linkedin/callback",
                    params={"code": "mock_auth_code"}
                )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["user"]["id"] == str(sample_user.id)
        assert data["created"] is False  # Existing user

    @pytest.mark.asyncio
    async def test_linkedin_callback_fails_with_invalid_code(
        self,
        client: AsyncClient
    ):
        """Test LinkedIn OAuth callback fails with invalid authorization code"""
        # Arrange
        # Mock failed token exchange
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(
                status_code=400,
                json=lambda: {"error": "invalid_grant"}
            )

            # Act
            response = await client.get(
                "/api/v1/auth/linkedin/callback",
                params={"code": "invalid_code"}
            )

        # Assert
        assert response.status_code == 400


@pytest.mark.integration
class TestPhoneVerification:
    """Integration tests for phone verification endpoints"""

    @pytest.mark.asyncio
    async def test_send_verification_code_success(
        self,
        client: AsyncClient,
        sample_user: User
    ):
        """Test sending verification code successfully"""
        # Arrange
        phone_number = "+14155551234"

        # Act
        response = await client.post(
            "/api/v1/auth/verify-phone",
            params={"user_id": str(sample_user.id)},
            json={"phone_number": phone_number}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["message"] == "Verification code sent successfully"
        assert data["phone_number"] == phone_number
        assert "expires_in_minutes" in data

    @pytest.mark.asyncio
    async def test_send_verification_code_invalid_phone_format(
        self,
        client: AsyncClient,
        sample_user: User
    ):
        """Test sending verification code with invalid phone format"""
        # Arrange
        invalid_phone = "1234567890"  # Missing +

        # Act
        response = await client.post(
            "/api/v1/auth/verify-phone",
            params={"user_id": str(sample_user.id)},
            json={"phone_number": invalid_phone}
        )

        # Assert
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_confirm_verification_code_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_user: User
    ):
        """Test confirming verification code successfully"""
        # Arrange
        phone_number = "+14155559999"
        verification_code = "123456"

        # Send verification code first
        await client.post(
            "/api/v1/auth/verify-phone",
            params={"user_id": str(sample_user.id)},
            json={"phone_number": phone_number}
        )

        # Get the actual code from database
        await db_session.refresh(sample_user)
        actual_code = sample_user.phone_verification_code

        # Act
        response = await client.post(
            "/api/v1/auth/confirm-phone",
            params={"user_id": str(sample_user.id)},
            json={
                "phone_number": phone_number,
                "verification_code": actual_code
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["verified"] is True
        assert data["phone_number"] == phone_number

    @pytest.mark.asyncio
    async def test_confirm_verification_code_invalid_code(
        self,
        client: AsyncClient,
        sample_user: User
    ):
        """Test confirming with invalid verification code"""
        # Arrange
        phone_number = "+14155558888"

        # Send verification code first
        await client.post(
            "/api/v1/auth/verify-phone",
            params={"user_id": str(sample_user.id)},
            json={"phone_number": phone_number}
        )

        # Act - Try with wrong code
        response = await client.post(
            "/api/v1/auth/confirm-phone",
            params={"user_id": str(sample_user.id)},
            json={
                "phone_number": phone_number,
                "verification_code": "999999"  # Wrong code
            }
        )

        # Assert
        assert response.status_code == 400


@pytest.mark.integration
class TestLogout:
    """Integration tests for logout endpoint"""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient):
        """Test logout endpoint returns success"""
        # Act
        response = await client.post("/api/v1/auth/logout")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
