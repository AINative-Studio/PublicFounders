"""
Integration Tests for Introductions API

Tests the full introduction request and execution flow including:
- Creating introduction requests
- Responding to requests
- Completing introductions
- Listing introductions
- Permission validation
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.services.introduction_service import IntroductionStatus

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
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()

    return {
        "id": intro_id,
        "requester_id": mock_user["id"],
        "target_id": mock_target_user["id"],
        "connector_id": None,
        "status": IntroductionStatus.PENDING.value,
        "requester_message": "I'd love to connect about SaaS scaling.",
        "response_message": None,
        "context": {},
        "requested_at": now,
        "responded_at": None,
        "completed_at": None,
        "expires_at": expires_at,
        "outcome": None,
        "outcome_notes": None,
        "created_at": now,
        "updated_at": now
    }


class TestRequestIntroduction:
    """Test POST /api/v1/introductions/request endpoint."""

    def test_request_introduction_success(self, mock_user, mock_target_user):
        """Test successful introduction request."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.introduction_service.zerodb_client') as mock_db, \
             patch('app.services.introduction_service.embedding_service') as mock_embed, \
             patch('app.services.introduction_service.rlhf_service') as mock_rlhf, \
             patch('app.services.introduction_service.cache_service') as mock_cache:

            # Setup mocks
            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_db.get_by_id = AsyncMock(side_effect=[
                mock_user,
                mock_target_user
            ])
            mock_db.query_rows = AsyncMock(return_value=[])
            mock_db.insert_rows = AsyncMock(return_value={"success": True})
            mock_embed.upsert_embedding = AsyncMock(return_value="embed_123")
            mock_rlhf.track_introduction_outcome = AsyncMock()
            mock_cache.delete_pattern = AsyncMock()

            # Make request
            response = client.post(
                "/api/v1/introductions/request",
                json={
                    "target_id": mock_target_user["id"],
                    "message": "I'd love to connect about SaaS scaling strategies.",
                    "context": {"reason": "complementary_expertise"}
                }
            )

            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["requester_id"] == mock_user["id"]
            assert data["target_id"] == mock_target_user["id"]
            assert data["status"] == IntroductionStatus.PENDING.value

    def test_request_introduction_invalid_message_too_short(self, mock_target_user):
        """Test request fails with message too short."""
        response = client.post(
            "/api/v1/introductions/request",
            json={
                "target_id": mock_target_user["id"],
                "message": "Hi"  # Too short
            }
        )

        assert response.status_code == 422  # Validation error

    def test_request_introduction_invalid_message_too_long(self, mock_target_user):
        """Test request fails with message too long."""
        long_message = "x" * 501  # Over 500 char limit

        response = client.post(
            "/api/v1/introductions/request",
            json={
                "target_id": mock_target_user["id"],
                "message": long_message
            }
        )

        assert response.status_code == 422  # Validation error

    def test_request_introduction_missing_target_id(self):
        """Test request fails without target_id."""
        response = client.post(
            "/api/v1/introductions/request",
            json={
                "message": "Test message"
            }
        )

        assert response.status_code == 422  # Validation error


class TestGetReceivedIntroductions:
    """Test GET /api/v1/introductions/received endpoint."""

    def test_get_received_introductions_success(self, mock_user, mock_introduction):
        """Test getting received introductions."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.introduction_service.cache_service') as mock_cache, \
             patch('app.services.introduction_service.zerodb_client') as mock_db:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_db.query_rows = AsyncMock(return_value=[mock_introduction])

            response = client.get("/api/v1/introductions/received")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 0

    def test_get_received_introductions_with_status_filter(self, mock_user):
        """Test filtering by status."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.introduction_service.cache_service') as mock_cache, \
             patch('app.services.introduction_service.zerodb_client') as mock_db:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_db.query_rows = AsyncMock(return_value=[])

            response = client.get(
                "/api/v1/introductions/received",
                params={"status": "pending"}
            )

            assert response.status_code == 200

    def test_get_received_introductions_with_pagination(self, mock_user):
        """Test pagination parameters."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.introduction_service.cache_service') as mock_cache, \
             patch('app.services.introduction_service.zerodb_client') as mock_db:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_db.query_rows = AsyncMock(return_value=[])

            response = client.get(
                "/api/v1/introductions/received",
                params={"limit": 10, "offset": 5}
            )

            assert response.status_code == 200

    def test_get_received_introductions_invalid_status(self, mock_user):
        """Test invalid status filter is rejected."""
        response = client.get(
            "/api/v1/introductions/received",
            params={"status": "invalid_status"}
        )

        assert response.status_code == 422  # Validation error


class TestGetSentIntroductions:
    """Test GET /api/v1/introductions/sent endpoint."""

    def test_get_sent_introductions_success(self, mock_user, mock_introduction):
        """Test getting sent introductions."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.introduction_service.cache_service') as mock_cache, \
             patch('app.services.introduction_service.zerodb_client') as mock_db:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_db.query_rows = AsyncMock(return_value=[mock_introduction])

            response = client.get("/api/v1/introductions/sent")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


class TestGetSpecificIntroduction:
    """Test GET /api/v1/introductions/{intro_id} endpoint."""

    def test_get_introduction_success(self, mock_user, mock_introduction):
        """Test getting specific introduction."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.api.v1.endpoints.introductions.zerodb_client') as mock_db:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_db.get_by_id = AsyncMock(return_value=mock_introduction)

            response = client.get(f"/api/v1/introductions/{mock_introduction['id']}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == mock_introduction["id"]

    def test_get_introduction_not_found(self, mock_user):
        """Test getting non-existent introduction."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.api.v1.endpoints.introductions.zerodb_client') as mock_db:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_db.get_by_id = AsyncMock(return_value=None)

            intro_id = str(uuid4())
            response = client.get(f"/api/v1/introductions/{intro_id}")

            assert response.status_code == 404

    def test_get_introduction_unauthorized(self, mock_user, mock_introduction):
        """Test cannot view introduction you're not part of."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.api.v1.endpoints.introductions.zerodb_client') as mock_db:

            # User not involved in introduction
            other_user = {**mock_user, "id": str(uuid4())}
            mock_auth.return_value = AsyncMock(return_value=other_user)
            mock_db.get_by_id = AsyncMock(return_value=mock_introduction)

            response = client.get(f"/api/v1/introductions/{mock_introduction['id']}")

            assert response.status_code == 403


class TestRespondToIntroduction:
    """Test PUT /api/v1/introductions/{intro_id}/respond endpoint."""

    def test_accept_introduction(self, mock_target_user, mock_introduction):
        """Test accepting an introduction."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.introduction_service.zerodb_client') as mock_db, \
             patch('app.services.introduction_service.rlhf_service') as mock_rlhf, \
             patch('app.services.introduction_service.cache_service') as mock_cache:

            mock_auth.return_value = AsyncMock(return_value=mock_target_user)
            mock_db.get_by_id = AsyncMock(side_effect=[
                mock_introduction,
                {**mock_introduction, "status": IntroductionStatus.ACCEPTED.value}
            ])
            mock_db.update_rows = AsyncMock()
            mock_rlhf.track_introduction_outcome = AsyncMock()
            mock_cache.delete_pattern = AsyncMock()

            response = client.put(
                f"/api/v1/introductions/{mock_introduction['id']}/respond",
                json={
                    "accept": True,
                    "message": "Happy to connect!"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == IntroductionStatus.ACCEPTED.value

    def test_decline_introduction(self, mock_target_user, mock_introduction):
        """Test declining an introduction."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.introduction_service.zerodb_client') as mock_db, \
             patch('app.services.introduction_service.rlhf_service') as mock_rlhf, \
             patch('app.services.introduction_service.cache_service') as mock_cache:

            mock_auth.return_value = AsyncMock(return_value=mock_target_user)
            mock_db.get_by_id = AsyncMock(side_effect=[
                mock_introduction,
                {**mock_introduction, "status": IntroductionStatus.DECLINED.value}
            ])
            mock_db.update_rows = AsyncMock()
            mock_rlhf.track_introduction_outcome = AsyncMock()
            mock_cache.delete_pattern = AsyncMock()

            response = client.put(
                f"/api/v1/introductions/{mock_introduction['id']}/respond",
                json={
                    "accept": False,
                    "message": "Not at this time, thanks."
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == IntroductionStatus.DECLINED.value


class TestCompleteIntroduction:
    """Test PUT /api/v1/introductions/{intro_id}/complete endpoint."""

    def test_complete_introduction_meeting_scheduled(self, mock_user, mock_introduction):
        """Test completing introduction with successful outcome."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.introduction_service.zerodb_client') as mock_db, \
             patch('app.services.introduction_service.rlhf_service') as mock_rlhf, \
             patch('app.services.introduction_service.cache_service') as mock_cache:

            accepted_intro = {
                **mock_introduction,
                "status": IntroductionStatus.ACCEPTED.value
            }

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_db.get_by_id = AsyncMock(side_effect=[
                accepted_intro,
                {**accepted_intro, "status": IntroductionStatus.COMPLETED.value}
            ])
            mock_db.update_rows = AsyncMock()
            mock_rlhf.track_introduction_outcome = AsyncMock()
            mock_cache.delete_pattern = AsyncMock()

            response = client.put(
                f"/api/v1/introductions/{mock_introduction['id']}/complete",
                json={
                    "outcome": "meeting_scheduled",
                    "notes": "Great call scheduled for next week!"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == IntroductionStatus.COMPLETED.value

    def test_complete_introduction_invalid_outcome(self, mock_user, mock_introduction):
        """Test completing with invalid outcome."""
        response = client.put(
            f"/api/v1/introductions/{mock_introduction['id']}/complete",
            json={
                "outcome": "invalid_outcome"
            }
        )

        assert response.status_code == 422  # Validation error

    def test_complete_introduction_missing_outcome(self, mock_user, mock_introduction):
        """Test completing without outcome."""
        response = client.put(
            f"/api/v1/introductions/{mock_introduction['id']}/complete",
            json={}
        )

        assert response.status_code == 422  # Validation error


class TestEndToEndFlow:
    """Test complete introduction flow."""

    def test_complete_introduction_flow(
        self,
        mock_user,
        mock_target_user
    ):
        """Test full flow: request -> accept -> complete."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.services.introduction_service.zerodb_client') as mock_db, \
             patch('app.services.introduction_service.embedding_service') as mock_embed, \
             patch('app.services.introduction_service.rlhf_service') as mock_rlhf, \
             patch('app.services.introduction_service.cache_service') as mock_cache:

            intro_id = str(uuid4())
            now = datetime.utcnow().isoformat()
            expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()

            # Step 1: Request introduction
            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_db.get_by_id = AsyncMock(side_effect=[
                mock_user,
                mock_target_user
            ])
            mock_db.query_rows = AsyncMock(return_value=[])
            mock_db.insert_rows = AsyncMock(return_value={"success": True})
            mock_embed.upsert_embedding = AsyncMock(return_value="embed_123")
            mock_rlhf.track_introduction_outcome = AsyncMock()
            mock_cache.delete_pattern = AsyncMock()
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()

            request_response = client.post(
                "/api/v1/introductions/request",
                json={
                    "target_id": mock_target_user["id"],
                    "message": "I'd love to connect about SaaS scaling."
                }
            )

            assert request_response.status_code == 201

            # Step 2: Target accepts
            pending_intro = {
                "id": intro_id,
                "requester_id": mock_user["id"],
                "target_id": mock_target_user["id"],
                "status": IntroductionStatus.PENDING.value,
                "requester_message": "I'd love to connect.",
                "expires_at": expires_at,
                "created_at": now,
                "updated_at": now
            }

            mock_auth.return_value = AsyncMock(return_value=mock_target_user)
            mock_db.get_by_id = AsyncMock(side_effect=[
                pending_intro,
                {**pending_intro, "status": IntroductionStatus.ACCEPTED.value}
            ])
            mock_db.update_rows = AsyncMock()

            accept_response = client.put(
                f"/api/v1/introductions/{intro_id}/respond",
                json={"accept": True, "message": "Happy to connect!"}
            )

            assert accept_response.status_code == 200

            # Step 3: Mark as completed
            accepted_intro = {
                **pending_intro,
                "status": IntroductionStatus.ACCEPTED.value
            }

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_db.get_by_id = AsyncMock(side_effect=[
                accepted_intro,
                {**accepted_intro, "status": IntroductionStatus.COMPLETED.value}
            ])

            complete_response = client.put(
                f"/api/v1/introductions/{intro_id}/complete",
                json={
                    "outcome": "meeting_scheduled",
                    "notes": "Great call scheduled!"
                }
            )

            assert complete_response.status_code == 200
            data = complete_response.json()
            assert data["status"] == IntroductionStatus.COMPLETED.value


class TestGetIntroductionSuggestions:
    """Test GET /api/v1/introductions/suggestions endpoint (Story 7.1)."""

    def test_get_suggestions_returns_valid_data(self, mock_user):
        """Test GET /suggestions returns valid suggestion data."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.api.v1.endpoints.introductions.matching_service') as mock_matching, \
             patch('app.api.v1.endpoints.introductions.cache_service') as mock_cache, \
             patch('app.api.v1.endpoints.introductions.rlhf_service') as mock_rlhf:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_cache.get_cached_discovery = AsyncMock(return_value=None)
            mock_cache.cache_discovery_results = AsyncMock()
            mock_rlhf.track_goal_match = AsyncMock()

            # Mock matching service to return suggestions
            mock_suggestions = [
                {
                    "target_user_id": str(uuid4()),
                    "target_name": "Jane Founder",
                    "target_headline": "CEO at AI Startup",
                    "target_location": "San Francisco, CA",
                    "match_score": {
                        "relevance_score": 0.85,
                        "trust_score": 0.75,
                        "reciprocity_score": 0.80,
                        "overall_score": 0.81
                    },
                    "reasoning": "Working on similar goals in AI and marketplace.",
                    "matching_goals": ["Raise seed round"],
                    "matching_asks": ["Intros to VCs"]
                }
            ]
            mock_matching.suggest_introductions = AsyncMock(return_value=mock_suggestions)

            response = client.get("/api/v1/introductions/suggestions")

            assert response.status_code == 200
            data = response.json()

            assert isinstance(data, list)
            assert len(data) > 0

            # Verify first suggestion structure
            suggestion = data[0]
            assert "target_user_id" in suggestion
            assert "target_name" in suggestion
            assert "match_score" in suggestion
            assert "reasoning" in suggestion
            assert "matching_goals" in suggestion
            assert "matching_asks" in suggestion

            # Verify match score structure
            match_score = suggestion["match_score"]
            assert "relevance_score" in match_score
            assert "trust_score" in match_score
            assert "reciprocity_score" in match_score
            assert "overall_score" in match_score

            # Verify score ranges
            assert 0.0 <= match_score["relevance_score"] <= 1.0
            assert 0.0 <= match_score["trust_score"] <= 1.0
            assert 0.0 <= match_score["reciprocity_score"] <= 1.0
            assert 0.0 <= match_score["overall_score"] <= 1.0

    def test_get_suggestions_authentication_required(self):
        """Test GET /suggestions requires authentication."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth:
            from fastapi import HTTPException
            mock_auth.side_effect = HTTPException(status_code=401, detail="Unauthorized")

            response = client.get("/api/v1/introductions/suggestions")

            assert response.status_code == 401

    def test_get_suggestions_query_parameter_validation(self, mock_user):
        """Test GET /suggestions validates query parameters."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth:
            mock_auth.return_value = AsyncMock(return_value=mock_user)

            # Test invalid limit (too high)
            response = client.get("/api/v1/introductions/suggestions?limit=100")
            assert response.status_code == 422  # Validation error

            # Test invalid min_score (out of range)
            response = client.get("/api/v1/introductions/suggestions?min_score=1.5")
            assert response.status_code == 422

            # Test invalid match_type
            response = client.get("/api/v1/introductions/suggestions?match_type=invalid")
            assert response.status_code == 422

    def test_get_suggestions_cache_hit(self, mock_user):
        """Test GET /suggestions returns cached results."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.api.v1.endpoints.introductions.cache_service') as mock_cache, \
             patch('app.api.v1.endpoints.introductions.matching_service') as mock_matching, \
             patch('app.api.v1.endpoints.introductions.rlhf_service') as mock_rlhf:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_rlhf.track_goal_match = AsyncMock()

            # Mock cache hit
            cached_data = [{
                "target_user_id": str(uuid4()),
                "target_name": "Cached User",
                "target_headline": "Cached Headline",
                "target_location": "SF",
                "match_score": {
                    "relevance_score": 0.9,
                    "trust_score": 0.8,
                    "reciprocity_score": 0.85,
                    "overall_score": 0.86
                },
                "reasoning": "Cached reasoning",
                "matching_goals": [],
                "matching_asks": []
            }]
            mock_cache.get_cached_discovery = AsyncMock(return_value=cached_data)

            response = client.get("/api/v1/introductions/suggestions")

            assert response.status_code == 200
            data = response.json()

            # Should return cached data
            assert len(data) == 1
            assert data[0]["target_name"] == "Cached User"

            # Matching service should NOT be called on cache hit
            mock_matching.suggest_introductions.assert_not_called()

    def test_get_suggestions_empty_results(self, mock_user):
        """Test GET /suggestions handles empty results gracefully."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.api.v1.endpoints.introductions.matching_service') as mock_matching, \
             patch('app.api.v1.endpoints.introductions.cache_service') as mock_cache, \
             patch('app.api.v1.endpoints.introductions.rlhf_service') as mock_rlhf:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_cache.get_cached_discovery = AsyncMock(return_value=None)
            mock_cache.cache_discovery_results = AsyncMock()
            mock_rlhf.track_goal_match = AsyncMock()

            # Mock empty suggestions
            mock_matching.suggest_introductions = AsyncMock(return_value=[])

            response = client.get("/api/v1/introductions/suggestions")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0

    def test_get_suggestions_with_match_type_filter(self, mock_user):
        """Test GET /suggestions with different match_type filters."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.api.v1.endpoints.introductions.matching_service') as mock_matching, \
             patch('app.api.v1.endpoints.introductions.cache_service') as mock_cache, \
             patch('app.api.v1.endpoints.introductions.rlhf_service') as mock_rlhf:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_cache.get_cached_discovery = AsyncMock(return_value=None)
            mock_cache.cache_discovery_results = AsyncMock()
            mock_rlhf.track_goal_match = AsyncMock()
            mock_matching.suggest_introductions = AsyncMock(return_value=[])

            # Test goal_based
            response = client.get("/api/v1/introductions/suggestions?match_type=goal_based")
            assert response.status_code == 200
            mock_matching.suggest_introductions.assert_called()
            call_args = mock_matching.suggest_introductions.call_args
            assert call_args.kwargs["match_type"] == "goal_based"

            # Test ask_based
            response = client.get("/api/v1/introductions/suggestions?match_type=ask_based")
            assert response.status_code == 200
            call_args = mock_matching.suggest_introductions.call_args
            assert call_args.kwargs["match_type"] == "ask_based"

            # Test all (default)
            response = client.get("/api/v1/introductions/suggestions?match_type=all")
            assert response.status_code == 200
            call_args = mock_matching.suggest_introductions.call_args
            assert call_args.kwargs["match_type"] == "all"

    def test_get_suggestions_with_min_score_filter(self, mock_user):
        """Test GET /suggestions with min_score parameter."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.api.v1.endpoints.introductions.matching_service') as mock_matching, \
             patch('app.api.v1.endpoints.introductions.cache_service') as mock_cache, \
             patch('app.api.v1.endpoints.introductions.rlhf_service') as mock_rlhf:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_cache.get_cached_discovery = AsyncMock(return_value=None)
            mock_cache.cache_discovery_results = AsyncMock()
            mock_rlhf.track_goal_match = AsyncMock()
            mock_matching.suggest_introductions = AsyncMock(return_value=[])

            # Test custom min_score
            response = client.get("/api/v1/introductions/suggestions?min_score=0.8")
            assert response.status_code == 200

            call_args = mock_matching.suggest_introductions.call_args
            assert call_args.kwargs["min_score"] == 0.8

    def test_get_suggestions_with_limit_parameter(self, mock_user):
        """Test GET /suggestions respects limit parameter."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.api.v1.endpoints.introductions.matching_service') as mock_matching, \
             patch('app.api.v1.endpoints.introductions.cache_service') as mock_cache, \
             patch('app.api.v1.endpoints.introductions.rlhf_service') as mock_rlhf:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_cache.get_cached_discovery = AsyncMock(return_value=None)
            mock_cache.cache_discovery_results = AsyncMock()
            mock_rlhf.track_goal_match = AsyncMock()

            # Create more suggestions than limit
            many_suggestions = [
                {
                    "target_user_id": str(uuid4()),
                    "target_name": f"User {i}",
                    "target_headline": "Founder",
                    "target_location": "SF",
                    "match_score": {
                        "relevance_score": 0.8,
                        "trust_score": 0.7,
                        "reciprocity_score": 0.75,
                        "overall_score": 0.76
                    },
                    "reasoning": "Match reason",
                    "matching_goals": [],
                    "matching_asks": []
                }
                for i in range(30)
            ]
            mock_matching.suggest_introductions = AsyncMock(return_value=many_suggestions)

            # Request with limit=10
            response = client.get("/api/v1/introductions/suggestions?limit=10")
            assert response.status_code == 200

            call_args = mock_matching.suggest_introductions.call_args
            assert call_args.kwargs["limit"] == 10

    def test_get_suggestions_error_handling(self, mock_user):
        """Test GET /suggestions handles service errors gracefully."""
        with patch('app.api.v1.endpoints.introductions.get_current_user') as mock_auth, \
             patch('app.api.v1.endpoints.introductions.matching_service') as mock_matching, \
             patch('app.api.v1.endpoints.introductions.cache_service') as mock_cache:

            mock_auth.return_value = AsyncMock(return_value=mock_user)
            mock_cache.get_cached_discovery = AsyncMock(return_value=None)

            # Mock service error
            from app.services.matching_service import MatchingServiceError
            mock_matching.suggest_introductions = AsyncMock(
                side_effect=MatchingServiceError("Service error")
            )

            response = client.get("/api/v1/introductions/suggestions")

            assert response.status_code == 500
            assert "Failed to generate suggestions" in response.json()["detail"]
