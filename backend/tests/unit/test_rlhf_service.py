"""
Unit tests for RLHF Service.

Test Coverage:
- Goal matching interaction tracking
- Ask matching interaction tracking
- Discovery interaction tracking
- Introduction outcome tracking
- Agent feedback submission
- RLHF insights retrieval
- Error tracking
- API error handling
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from app.services.rlhf_service import RLHFService, RLHFServiceError


class TestRLHFService:
    """Test RLHF Service functionality."""

    @pytest.fixture
    def rlhf_service(self):
        """Create RLHF service instance for testing."""
        return RLHFService()

    @pytest.mark.asyncio
    async def test_track_goal_match_success(self, rlhf_service):
        """Test successful goal matching interaction tracking."""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock ZeroDB API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"interaction_id": "interaction_123"}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            query_goal_id = uuid4()
            matched_ids = [uuid4(), uuid4(), uuid4()]
            scores = [0.95, 0.87, 0.75]

            interaction_id = await rlhf_service.track_goal_match(
                query_goal_id=query_goal_id,
                query_goal_description="Raise $2M seed round",
                matched_goal_ids=matched_ids,
                similarity_scores=scores,
                context={"user_id": str(uuid4()), "goal_type": "fundraising"}
            )

            assert interaction_id == "interaction_123"

            # Verify API call was made
            mock_client.return_value.__aenter__.return_value.post.assert_called_once()
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            payload = call_args[1]["json"]

            assert payload["agent_id"] == "goal_matcher"
            assert "Raise $2M seed round" in payload["prompt"]
            assert payload["feedback"] == 0.0  # Neutral initially
            assert payload["context"]["matched_count"] == 3
            assert payload["context"]["top_score"] == 0.95

    @pytest.mark.asyncio
    async def test_track_goal_match_api_error(self, rlhf_service):
        """Test goal matching tracking handles API errors."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPError("API Error")

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(RLHFServiceError):
                await rlhf_service.track_goal_match(
                    query_goal_id=uuid4(),
                    query_goal_description="Test goal",
                    matched_goal_ids=[uuid4()],
                    similarity_scores=[0.9],
                    context={}
                )

    @pytest.mark.asyncio
    async def test_track_ask_match_success(self, rlhf_service):
        """Test successful ask matching interaction tracking."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"interaction_id": "interaction_456"}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            query_ask_id = uuid4()
            matched_ids = [uuid4(), uuid4()]
            scores = [0.92, 0.83]

            interaction_id = await rlhf_service.track_ask_match(
                query_ask_id=query_ask_id,
                query_ask_description="Need intros to VCs",
                matched_ask_ids=matched_ids,
                similarity_scores=scores,
                context={"user_id": str(uuid4()), "urgency": "high"}
            )

            assert interaction_id == "interaction_456"

            # Verify payload
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            payload = call_args[1]["json"]

            assert payload["agent_id"] == "ask_matcher"
            assert "Need intros to VCs" in payload["prompt"]
            assert payload["context"]["urgency"] == "high"

    @pytest.mark.asyncio
    async def test_track_discovery_interaction_with_click(self, rlhf_service):
        """Test discovery interaction tracking with post click."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"interaction_id": "interaction_789"}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            user_id = uuid4()
            shown_posts = [uuid4(), uuid4(), uuid4()]
            clicked_post = shown_posts[1]

            interaction_id = await rlhf_service.track_discovery_interaction(
                user_id=user_id,
                user_goals=["Raise funding", "Hire engineers"],
                shown_posts=shown_posts,
                clicked_post_id=clicked_post
            )

            assert interaction_id == "interaction_789"

            # Verify feedback is positive for clicks
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            payload = call_args[1]["json"]

            assert payload["agent_id"] == "discovery_feed"
            assert payload["feedback"] == 0.5  # Positive feedback for click
            assert payload["context"]["clicked_post"] == str(clicked_post)

    @pytest.mark.asyncio
    async def test_track_discovery_interaction_no_click(self, rlhf_service):
        """Test discovery interaction tracking without post click."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"interaction_id": "interaction_012"}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            user_id = uuid4()
            shown_posts = [uuid4(), uuid4()]

            interaction_id = await rlhf_service.track_discovery_interaction(
                user_id=user_id,
                user_goals=["Build product"],
                shown_posts=shown_posts,
                clicked_post_id=None
            )

            assert interaction_id == "interaction_012"

            # Verify feedback is neutral without clicks
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            payload = call_args[1]["json"]

            assert payload["feedback"] == 0.0  # Neutral feedback
            assert payload["context"]["clicked_post"] is None

    @pytest.mark.asyncio
    async def test_track_introduction_outcome_accepted(self, rlhf_service):
        """Test introduction outcome tracking for accepted intro."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"interaction_id": "intro_123"}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            intro_id = uuid4()
            from_user = uuid4()
            to_user = uuid4()

            interaction_id = await rlhf_service.track_introduction_outcome(
                intro_id=intro_id,
                from_user_id=from_user,
                to_user_id=to_user,
                outcome="accepted",
                value_score=1.0
            )

            assert interaction_id == "intro_123"

            # Verify positive feedback for accepted intro
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            payload = call_args[1]["json"]

            assert payload["agent_id"] == "smart_introductions"
            assert payload["feedback"] == 1.0
            assert payload["context"]["outcome"] == "accepted"

    @pytest.mark.asyncio
    async def test_track_introduction_outcome_declined(self, rlhf_service):
        """Test introduction outcome tracking for declined intro."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"interaction_id": "intro_456"}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            intro_id = uuid4()

            interaction_id = await rlhf_service.track_introduction_outcome(
                intro_id=intro_id,
                from_user_id=uuid4(),
                to_user_id=uuid4(),
                outcome="declined",
                value_score=-0.5
            )

            assert interaction_id == "intro_456"

            # Verify negative feedback for declined intro
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            payload = call_args[1]["json"]

            assert payload["feedback"] == -0.5
            assert payload["context"]["outcome"] == "declined"

    @pytest.mark.asyncio
    async def test_provide_agent_feedback_thumbs_up(self, rlhf_service):
        """Test providing thumbs up agent feedback."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"feedback_id": "feedback_123"}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            feedback_id = await rlhf_service.provide_agent_feedback(
                agent_id="goal_matcher",
                feedback_type="thumbs_up",
                comment="Great matching!"
            )

            assert feedback_id == "feedback_123"

            # Verify payload
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            payload = call_args[1]["json"]

            assert payload["agent_id"] == "goal_matcher"
            assert payload["feedback_type"] == "thumbs_up"
            assert payload["comment"] == "Great matching!"

    @pytest.mark.asyncio
    async def test_provide_agent_feedback_rating(self, rlhf_service):
        """Test providing rating agent feedback."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"feedback_id": "feedback_456"}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            feedback_id = await rlhf_service.provide_agent_feedback(
                agent_id="discovery_feed",
                feedback_type="rating",
                rating=4.5
            )

            assert feedback_id == "feedback_456"

            # Verify rating is included
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            payload = call_args[1]["json"]

            assert payload["rating"] == 4.5

    @pytest.mark.asyncio
    async def test_get_rlhf_insights_success(self, rlhf_service):
        """Test retrieving RLHF insights."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "total_interactions": 150,
                "agents": [
                    {"agent_id": "goal_matcher", "avg_feedback": 0.75},
                    {"agent_id": "discovery_feed", "avg_feedback": 0.65}
                ]
            }
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            insights = await rlhf_service.get_rlhf_insights(time_range="day")

            assert insights["total_interactions"] == 150
            assert len(insights["agents"]) == 2
            assert insights["agents"][0]["agent_id"] == "goal_matcher"

    @pytest.mark.asyncio
    async def test_get_rlhf_insights_api_error(self, rlhf_service):
        """Test RLHF insights handles API errors gracefully."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPError("API Error")

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            # Should not raise, returns empty insights
            insights = await rlhf_service.get_rlhf_insights()

            assert "error" in insights
            assert insights["total_interactions"] == 0

    @pytest.mark.asyncio
    async def test_track_error_success(self, rlhf_service):
        """Test error tracking."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"error_id": "error_123"}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            error_id = await rlhf_service.track_error(
                error_type="embedding_error",
                error_message="Failed to generate embedding",
                severity="high",
                context={"entity_type": "goal", "user_id": str(uuid4())}
            )

            assert error_id == "error_123"

    @pytest.mark.asyncio
    async def test_track_error_handles_failure_gracefully(self, rlhf_service):
        """Test error tracking doesn't raise on failure."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPError("API Error")

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            # Should not raise, returns empty string
            error_id = await rlhf_service.track_error(
                error_type="test_error",
                error_message="Test",
                severity="low"
            )

            assert error_id == ""

    @pytest.mark.asyncio
    async def test_track_goal_match_empty_results(self, rlhf_service):
        """Test goal matching with no results."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"interaction_id": "interaction_empty"}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            interaction_id = await rlhf_service.track_goal_match(
                query_goal_id=uuid4(),
                query_goal_description="Obscure goal with no matches",
                matched_goal_ids=[],
                similarity_scores=[],
                context={}
            )

            assert interaction_id == "interaction_empty"

            # Verify context reflects no matches
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            payload = call_args[1]["json"]

            assert payload["context"]["matched_count"] == 0
            assert payload["context"]["top_score"] == 0.0
            assert "No matches found" in payload["response"]
