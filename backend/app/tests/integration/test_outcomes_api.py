"""
Integration Tests for Outcomes API

Tests the full outcome tracking flow including:
- Recording outcomes
- Retrieving outcomes
- Updating outcomes
- Getting analytics
- Permission validation
- Error handling

Story 8.1: Record Intro Outcome
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.schemas.outcome import OutcomeType

client = TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "id": str(uuid4()),
        "email": "test@example.com",
        "name": "Test User"
    }


@pytest.fixture
def mock_target_user():
    """Mock target user for introductions."""
    return {
        "id": str(uuid4()),
        "email": "target@example.com",
        "name": "Target User"
    }


@pytest.fixture
def mock_introduction(mock_user, mock_target_user):
    """Mock introduction data."""
    intro_id = str(uuid4())
    now = datetime.utcnow().isoformat()

    return {
        "id": intro_id,
        "requester_id": mock_user["id"],
        "target_id": mock_target_user["id"],
        "connector_id": None,
        "status": "accepted",
        "requester_message": "Let's connect!",
        "response_message": "Sure!",
        "context": {},
        "requested_at": now,
        "responded_at": now,
        "completed_at": None,
        "created_at": now,
        "updated_at": now
    }


@pytest.fixture
def mock_outcome(mock_introduction, mock_user):
    """Mock outcome data."""
    outcome_id = str(uuid4())
    now = datetime.utcnow().isoformat()

    return {
        "id": outcome_id,
        "introduction_id": mock_introduction["id"],
        "user_id": mock_user["id"],
        "outcome_type": OutcomeType.SUCCESSFUL.value,
        "feedback_text": "Great conversation! We're scheduling a follow-up.",
        "rating": 5,
        "tags": ["partnership", "follow-up"],
        "created_at": now,
        "updated_at": now
    }


class TestRecordOutcome:
    """Test POST /api/v1/introductions/{intro_id}/outcome endpoint."""

    def test_record_outcome_success(
        self,
        mock_user,
        mock_introduction
    ):
        """Test successful outcome recording."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.outcome_service.zerodb_client') as mock_db, \
             patch('app.services.outcome_service.rlhf_service') as mock_rlhf, \
             patch('app.services.outcome_service.cache_service') as mock_cache:

            # Setup mocks
            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_db.get_by_id = AsyncMock(return_value=mock_introduction)
            mock_db.query_rows = AsyncMock(return_value=[])  # No existing outcome
            mock_db.insert_rows = AsyncMock(return_value={"success": True})
            mock_rlhf.track_introduction_outcome = AsyncMock()
            mock_cache.delete = AsyncMock()

            # Make request
            response = client.post(
                f"/api/v1/introductions/{mock_introduction['id']}/outcome",
                json={
                    "outcome_type": "successful",
                    "feedback_text": "Great conversation! We're scheduling a follow-up.",
                    "rating": 5,
                    "tags": ["partnership", "follow-up"]
                }
            )

            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["introduction_id"] == mock_introduction["id"]
            assert data["user_id"] == mock_user["id"]
            assert data["outcome_type"] == "successful"
            assert data["rating"] == 5
            assert "partnership" in data["tags"]

    def test_record_outcome_minimal_data(
        self,
        mock_user,
        mock_introduction
    ):
        """Test recording outcome with only required fields."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.outcome_service.zerodb_client') as mock_db, \
             patch('app.services.outcome_service.rlhf_service') as mock_rlhf, \
             patch('app.services.outcome_service.cache_service') as mock_cache:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_db.get_by_id = AsyncMock(return_value=mock_introduction)
            mock_db.query_rows = AsyncMock(return_value=[])
            mock_db.insert_rows = AsyncMock(return_value={"success": True})
            mock_rlhf.track_introduction_outcome = AsyncMock()
            mock_cache.delete = AsyncMock()

            response = client.post(
                f"/api/v1/introductions/{mock_introduction['id']}/outcome",
                json={
                    "outcome_type": "no_response"
                }
            )

            assert response.status_code == 201
            data = response.json()
            assert data["outcome_type"] == "no_response"
            assert data["feedback_text"] is None
            assert data["rating"] is None

    def test_record_outcome_invalid_type(
        self,
        mock_introduction
    ):
        """Test recording outcome with invalid type."""
        response = client.post(
            f"/api/v1/introductions/{mock_introduction['id']}/outcome",
            json={
                "outcome_type": "invalid_type"
            }
        )

        assert response.status_code == 422  # Validation error

    def test_record_outcome_feedback_too_short(
        self,
        mock_introduction
    ):
        """Test recording outcome with feedback text too short."""
        response = client.post(
            f"/api/v1/introductions/{mock_introduction['id']}/outcome",
            json={
                "outcome_type": "successful",
                "feedback_text": "Short"  # Less than 10 chars
            }
        )

        assert response.status_code == 422  # Validation error

    def test_record_outcome_feedback_too_long(
        self,
        mock_introduction
    ):
        """Test recording outcome with feedback text too long."""
        long_feedback = "x" * 501  # Over 500 char limit

        response = client.post(
            f"/api/v1/introductions/{mock_introduction['id']}/outcome",
            json={
                "outcome_type": "successful",
                "feedback_text": long_feedback
            }
        )

        assert response.status_code == 422  # Validation error

    def test_record_outcome_invalid_rating(
        self,
        mock_introduction
    ):
        """Test recording outcome with invalid rating."""
        response = client.post(
            f"/api/v1/introductions/{mock_introduction['id']}/outcome",
            json={
                "outcome_type": "successful",
                "rating": 6  # Over 5 max
            }
        )

        assert response.status_code == 422  # Validation error

    def test_record_outcome_introduction_not_found(
        self,
        mock_user
    ):
        """Test recording outcome for non-existent introduction."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.outcome_service.zerodb_client') as mock_db:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_db.get_by_id = AsyncMock(return_value=None)

            intro_id = str(uuid4())
            response = client.post(
                f"/api/v1/introductions/{intro_id}/outcome",
                json={
                    "outcome_type": "successful"
                }
            )

            assert response.status_code == 400
            assert "Introduction not found" in response.json()["detail"]

    def test_record_outcome_already_exists(
        self,
        mock_user,
        mock_introduction,
        mock_outcome
    ):
        """Test recording outcome when one already exists."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.outcome_service.zerodb_client') as mock_db:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_db.get_by_id = AsyncMock(return_value=mock_introduction)
            mock_db.query_rows = AsyncMock(return_value=[mock_outcome])

            response = client.post(
                f"/api/v1/introductions/{mock_introduction['id']}/outcome",
                json={
                    "outcome_type": "successful"
                }
            )

            assert response.status_code == 400
            assert "already exists" in response.json()["detail"]


class TestGetOutcome:
    """Test GET /api/v1/introductions/{intro_id}/outcome endpoint."""

    def test_get_outcome_success(
        self,
        mock_user,
        mock_outcome
    ):
        """Test successful outcome retrieval."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.outcome_service.cache_service') as mock_cache, \
             patch('app.services.outcome_service.zerodb_client') as mock_db:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_cache.get = AsyncMock(return_value=None)
            mock_db.query_rows = AsyncMock(return_value=[mock_outcome])
            mock_cache.set = AsyncMock()

            response = client.get(
                f"/api/v1/introductions/{mock_outcome['introduction_id']}/outcome"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == mock_outcome["id"]
            assert data["outcome_type"] == mock_outcome["outcome_type"]

    def test_get_outcome_not_found(
        self,
        mock_user
    ):
        """Test getting outcome that doesn't exist."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.outcome_service.cache_service') as mock_cache, \
             patch('app.services.outcome_service.zerodb_client') as mock_db:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_cache.get = AsyncMock(return_value=None)
            mock_db.query_rows = AsyncMock(return_value=[])

            intro_id = str(uuid4())
            response = client.get(
                f"/api/v1/introductions/{intro_id}/outcome"
            )

            assert response.status_code == 404
            assert "No outcome recorded" in response.json()["detail"]


class TestUpdateOutcome:
    """Test PATCH /api/v1/introductions/{intro_id}/outcome endpoint."""

    def test_update_outcome_success(
        self,
        mock_user,
        mock_introduction,
        mock_outcome
    ):
        """Test successful outcome update."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.outcome_service.zerodb_client') as mock_db, \
             patch('app.services.outcome_service.cache_service') as mock_cache, \
             patch('app.services.outcome_service.rlhf_service') as mock_rlhf:

            # Setup mocks
            mock_auth.return_value = AsyncMock(return_value=mock_user)

            # Mock get_outcome to return existing outcome
            with patch('app.services.outcome_service.outcome_service.get_outcome') as mock_get:
                mock_get.return_value = AsyncMock(return_value=mock_outcome)

                mock_db.get_by_id = AsyncMock(return_value=mock_introduction)
                updated_outcome = {**mock_outcome, "rating": 4}
                mock_db.update_rows = AsyncMock(return_value={"success": True})
                mock_db.query_rows = AsyncMock(return_value=[updated_outcome])
                mock_cache.delete = AsyncMock()
                mock_rlhf.track_introduction_outcome = AsyncMock()

                response = client.patch(
                    f"/api/v1/introductions/{mock_introduction['id']}/outcome",
                    json={
                        "rating": 4
                    }
                )

                assert response.status_code == 200
                data = response.json()
                assert data["rating"] == 4

    def test_update_outcome_no_fields(
        self,
        mock_introduction
    ):
        """Test updating outcome with no fields provided."""
        response = client.patch(
            f"/api/v1/introductions/{mock_introduction['id']}/outcome",
            json={}
        )

        assert response.status_code == 400
        assert "at least one field" in response.json()["detail"].lower()

    def test_update_outcome_not_found(
        self,
        mock_user,
        mock_introduction
    ):
        """Test updating non-existent outcome."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.outcome_service.zerodb_client') as mock_db:

            mock_auth.return_value = AsyncMock(return_value=mock_user)

            with patch('app.services.outcome_service.outcome_service.get_outcome') as mock_get:
                mock_get.return_value = AsyncMock(return_value=None)
                mock_db.get_by_id = AsyncMock(return_value=mock_introduction)

                response = client.patch(
                    f"/api/v1/introductions/{mock_introduction['id']}/outcome",
                    json={
                        "rating": 4
                    }
                )

                assert response.status_code == 400
                assert "Outcome not found" in response.json()["detail"]


class TestGetAnalytics:
    """Test GET /api/v1/outcomes/analytics endpoint."""

    def test_get_analytics_with_data(
        self,
        mock_user
    ):
        """Test getting analytics with outcome data."""
        user_id = uuid4()
        mock_user_with_id = {**mock_user, "id": str(user_id)}

        # Mock outcomes
        outcomes = [
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "outcome_type": "successful",
                "rating": 5,
                "tags": ["partnership"],
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "outcome_type": "successful",
                "rating": 4,
                "tags": ["follow-up"],
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "outcome_type": "unsuccessful",
                "rating": 3,
                "tags": [],
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.outcome_service.zerodb_client') as mock_db:

            mock_auth.return_value = AsyncMock(return_value=mock_user_with_id)
            mock_db.query_rows = AsyncMock(return_value=outcomes)

            response = client.get("/api/v1/outcomes/analytics")

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == str(user_id)
            assert data["total_outcomes"] == 3
            assert data["success_rate"] > 0
            assert data["average_rating"] is not None

    def test_get_analytics_no_data(
        self,
        mock_user
    ):
        """Test getting analytics with no outcomes."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.outcome_service.zerodb_client') as mock_db:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_db.query_rows = AsyncMock(return_value=[])

            response = client.get("/api/v1/outcomes/analytics")

            assert response.status_code == 200
            data = response.json()
            assert data["total_outcomes"] == 0
            assert data["success_rate"] == 0.0
            assert data["average_rating"] is None


class TestPermissions:
    """Test permission validation for outcomes."""

    def test_record_outcome_unauthorized_user(
        self,
        mock_user,
        mock_target_user,
        mock_introduction
    ):
        """Test that non-participants cannot record outcomes."""
        unauthorized_user = {
            "id": str(uuid4()),
            "email": "unauthorized@example.com",
            "name": "Unauthorized User"
        }

        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.outcome_service.zerodb_client') as mock_db:

            mock_auth.return_value = AsyncMock(return_value=unauthorized_user)
            mock_db.get_by_id = AsyncMock(return_value=mock_introduction)

            response = client.post(
                f"/api/v1/introductions/{mock_introduction['id']}/outcome",
                json={
                    "outcome_type": "successful"
                }
            )

            assert response.status_code == 400
            assert "participants" in response.json()["detail"].lower()

    def test_target_can_record_outcome(
        self,
        mock_target_user,
        mock_introduction
    ):
        """Test that target user can record outcomes."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.outcome_service.zerodb_client') as mock_db, \
             patch('app.services.outcome_service.rlhf_service') as mock_rlhf, \
             patch('app.services.outcome_service.cache_service') as mock_cache:

            mock_auth.return_value = AsyncMock(return_value=mock_target_user)
            mock_db.get_by_id = AsyncMock(return_value=mock_introduction)
            mock_db.query_rows = AsyncMock(return_value=[])
            mock_db.insert_rows = AsyncMock(return_value={"success": True})
            mock_rlhf.track_introduction_outcome = AsyncMock()
            mock_cache.delete = AsyncMock()

            response = client.post(
                f"/api/v1/introductions/{mock_introduction['id']}/outcome",
                json={
                    "outcome_type": "successful"
                }
            )

            assert response.status_code == 201


class TestValidation:
    """Test input validation for outcomes."""

    def test_empty_tags_not_allowed(
        self,
        mock_introduction
    ):
        """Test that empty tags are not allowed."""
        response = client.post(
            f"/api/v1/introductions/{mock_introduction['id']}/outcome",
            json={
                "outcome_type": "successful",
                "tags": ["valid-tag", "", "another-tag"]
            }
        )

        assert response.status_code == 422  # Validation error

    def test_tag_length_validation(
        self,
        mock_introduction
    ):
        """Test that tags over 50 chars are rejected."""
        long_tag = "x" * 51

        response = client.post(
            f"/api/v1/introductions/{mock_introduction['id']}/outcome",
            json={
                "outcome_type": "successful",
                "tags": [long_tag]
            }
        )

        assert response.status_code == 422  # Validation error

    def test_max_tags_validation(
        self,
        mock_introduction
    ):
        """Test that more than 10 tags are rejected."""
        too_many_tags = [f"tag-{i}" for i in range(11)]

        response = client.post(
            f"/api/v1/introductions/{mock_introduction['id']}/outcome",
            json={
                "outcome_type": "successful",
                "tags": too_many_tags
            }
        )

        assert response.status_code == 422  # Validation error
