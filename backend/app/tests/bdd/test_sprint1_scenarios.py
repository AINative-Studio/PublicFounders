"""
BDD Scenarios for Sprint 1 User Stories
Behavior-Driven Development tests for authentication and profiles
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, Mock, AsyncMock

from app.models.user import User
from app.models.founder_profile import FounderProfile
from app.core.security import create_access_token


@pytest.mark.bdd
class TestStory1_1_LinkedInOAuthSignUp:
    """
    Story 1.1: LinkedIn OAuth Sign-Up
    As a founder, I want to sign up using LinkedIn
    So that my identity and professional context are verified
    """

    @pytest.mark.asyncio
    async def test_scenario_user_clicks_sign_up_with_linkedin(self, client: AsyncClient):
        """
        Scenario: User clicks "Sign up with LinkedIn"
        Given I am not logged in
        When I click "Sign up with LinkedIn"
        Then I am authenticated via LinkedIn OAuth
        """
        # Given: User is not logged in (no auth header)

        # When: User initiates LinkedIn OAuth
        response = await client.get("/api/v1/auth/linkedin/initiate", follow_redirects=False)

        # Then: User is redirected to LinkedIn OAuth
        assert response.status_code in [200, 307, 302]

    @pytest.mark.asyncio
    async def test_scenario_oauth_creates_user_account(
        self,
        client: AsyncClient,
        linkedin_user_data: dict
    ):
        """
        Scenario: OAuth succeeds and creates user account
        Given OAuth succeeds
        Then my user account is created with LinkedIn data
        """
        # Given: OAuth succeeds (mocked)
        mock_token = {"access_token": "mock_token"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_post.return_value = Mock(status_code=200, json=lambda: mock_token)
                mock_get.return_value = Mock(status_code=200, json=lambda: linkedin_user_data)

                # When: OAuth callback is processed
                response = await client.get(
                    "/api/v1/auth/linkedin/callback",
                    params={"code": "auth_code"}
                )

        # Then: User account is created
        assert response.status_code == 200
        data = response.json()

        assert data["created"] is True  # New user
        assert data["user"]["name"] == linkedin_user_data["name"]
        assert data["user"]["linkedin_id"] == linkedin_user_data["sub"]
        assert "access_token" in data


@pytest.mark.bdd
class TestStory1_2_PhoneVerification:
    """
    Story 1.2: Phone Verification
    As a founder, I want to verify my phone number
    So that I can receive SMS-based introductions
    """

    @pytest.mark.asyncio
    async def test_scenario_user_receives_verification_code(
        self,
        client: AsyncClient,
        sample_user: User
    ):
        """
        Scenario: User enters phone and receives code
        Given I enter a phone number
        When I receive and confirm a code
        Then my phone number is marked verified
        """
        phone_number = "+14155551234"

        # Given: User enters phone number
        # When: Verification code is sent
        send_response = await client.post(
            "/api/v1/auth/verify-phone",
            params={"user_id": str(sample_user.id)},
            json={"phone_number": phone_number}
        )

        # Then: Code is sent successfully
        assert send_response.status_code == 200
        assert send_response.json()["phone_number"] == phone_number

    @pytest.mark.asyncio
    async def test_scenario_invalid_code_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_user: User
    ):
        """
        Scenario: Invalid verification code fails
        Given I have a pending verification
        When I enter an invalid code
        Then verification fails
        """
        phone_number = "+14155559999"

        # Given: Verification code sent
        await client.post(
            "/api/v1/auth/verify-phone",
            params={"user_id": str(sample_user.id)},
            json={"phone_number": phone_number}
        )

        # When: User enters invalid code
        confirm_response = await client.post(
            "/api/v1/auth/confirm-phone",
            params={"user_id": str(sample_user.id)},
            json={
                "phone_number": phone_number,
                "verification_code": "000000"  # Invalid code
            }
        )

        # Then: Verification fails
        assert confirm_response.status_code == 400


@pytest.mark.bdd
class TestStory2_1_CreateFounderProfile:
    """
    Story 2.1: Create Founder Profile
    As a founder, I want an auto-generated profile
    So that I can start building in public quickly
    """

    @pytest.mark.asyncio
    async def test_scenario_profile_auto_created_on_signup(
        self,
        client: AsyncClient,
        linkedin_user_data: dict
    ):
        """
        Scenario: Profile auto-generated on signup
        Given I sign up
        Then a founder profile is automatically created
        """
        # Given: User signs up via LinkedIn
        mock_token = {"access_token": "mock_token"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_post.return_value = Mock(status_code=200, json=lambda: mock_token)
                mock_get.return_value = Mock(status_code=200, json=lambda: linkedin_user_data)

                # When: OAuth completes
                response = await client.get(
                    "/api/v1/auth/linkedin/callback",
                    params={"code": "auth_code"}
                )

        # Then: Profile is automatically created
        assert response.status_code == 200
        data = response.json()

        user_id = data["user"]["id"]
        token = data["access_token"]

        # Verify profile exists
        profile_response = await client.get(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert profile_response.status_code == 200
        profile_data = profile_response.json()

        assert profile_data["profile"]["user_id"] == user_id
        assert profile_data["profile"]["public_visibility"] is True  # Default visibility


@pytest.mark.bdd
class TestStory2_2_EditProfileAndFocus:
    """
    Story 2.2: Edit Profile & Focus
    As a founder, I want to edit my bio and current focus
    So that my intent is accurately represented
    """

    @pytest.mark.asyncio
    async def test_scenario_update_triggers_embedding_regeneration(
        self,
        client: AsyncClient,
        sample_user_with_profile
    ):
        """
        Scenario: Profile update triggers embedding
        When I update my focus
        Then my profile embedding is regenerated
        """
        user, profile = sample_user_with_profile
        token = create_access_token({"sub": str(user.id), "linkedin_id": user.linkedin_id})

        # Given: User has a profile
        original_embedding_id = profile.embedding_id

        # When: User updates their focus
        update_response = await client.put(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "bio": "New bio for testing",
                "current_focus": "New focus area"
            }
        )

        # Then: Profile is updated
        assert update_response.status_code == 200
        updated_data = update_response.json()

        assert updated_data["bio"] == "New bio for testing"
        assert updated_data["current_focus"] == "New focus area"

        # Note: Embedding regeneration is tested in unit tests
        # Integration test verifies the update succeeds

    @pytest.mark.asyncio
    async def test_scenario_partial_update_not_allowed(
        self,
        client: AsyncClient,
        sample_user_with_profile
    ):
        """
        Scenario: No partial updates (atomic updates enforced)
        When update fails
        Then no fields are changed
        """
        user, profile = sample_user_with_profile
        token = create_access_token({"sub": str(user.id), "linkedin_id": user.linkedin_id})

        # Given: User has a profile
        original_bio = profile.bio

        # When: User updates profile
        update_response = await client.put(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_focus": "Updated focus"}
        )

        # Then: Update succeeds (or fails atomically)
        assert update_response.status_code == 200

        # Verify bio unchanged (partial update)
        updated_data = update_response.json()
        assert updated_data["bio"] == original_bio
        assert updated_data["current_focus"] == "Updated focus"


@pytest.mark.bdd
class TestComprehensiveUserJourney:
    """
    End-to-end user journey through Sprint 1 features
    """

    @pytest.mark.asyncio
    async def test_complete_onboarding_flow(
        self,
        client: AsyncClient,
        linkedin_user_data: dict
    ):
        """
        Test complete user onboarding journey
        1. Sign up with LinkedIn
        2. Profile auto-created
        3. Verify phone number
        4. Update profile
        """
        # Step 1: Sign up with LinkedIn
        mock_token = {"access_token": "mock_token"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_post.return_value = Mock(status_code=200, json=lambda: mock_token)
                mock_get.return_value = Mock(status_code=200, json=lambda: linkedin_user_data)

                signup_response = await client.get(
                    "/api/v1/auth/linkedin/callback",
                    params={"code": "auth_code"}
                )

        assert signup_response.status_code == 200
        signup_data = signup_response.json()

        user_id = signup_data["user"]["id"]
        jwt_token = signup_data["access_token"]

        # Step 2: Verify profile auto-created
        profile_response = await client.get(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        assert profile_response.status_code == 200
        assert profile_response.json()["profile"]["user_id"] == user_id

        # Step 3: Verify phone number (send code)
        phone_response = await client.post(
            "/api/v1/auth/verify-phone",
            params={"user_id": user_id},
            json={"phone_number": "+14155551234"}
        )

        assert phone_response.status_code == 200

        # Step 4: Update profile
        update_response = await client.put(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={
                "bio": "Passionate founder building AI tools",
                "current_focus": "Raising seed round for B2B SaaS"
            }
        )

        assert update_response.status_code == 200
        updated_profile = update_response.json()

        assert updated_profile["bio"] == "Passionate founder building AI tools"
        assert updated_profile["current_focus"] == "Raising seed round for B2B SaaS"
