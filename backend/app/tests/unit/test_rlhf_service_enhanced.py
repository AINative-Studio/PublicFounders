"""
Unit tests for Enhanced RLHF Service (Epic 8: Outcomes & Learning).

Tests cover:
- Introduction tracking with full context
- Feedback score calculation
- Match quality metrics
- Factor importance analysis
- Training dataset export
- User-specific success rate calculation
"""
import pytest
from datetime import datetime
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, Mock, patch

from app.services.rlhf_service import RLHFService, RLHFServiceError


@pytest.fixture
def rlhf_service():
    """Create RLHF service instance for testing."""
    return RLHFService()


@pytest.fixture
def sample_match_scores():
    """Sample match scores."""
    return {
        "relevance": 0.85,
        "trust": 0.72,
        "reciprocity": 0.80,
        "overall": 0.81
    }


@pytest.fixture
def sample_matching_context():
    """Sample matching context."""
    return {
        "goal_matches": ["goal_1", "goal_2"],
        "ask_matches": ["ask_1"],
        "top_similarity": 0.89,
        "avg_similarity": 0.82,
        "match_type": "goal_based",
        "goal_types": ["fundraising", "hiring"],
        "industry_match": True,
        "location_match": False
    }


@pytest.fixture
def sample_outcome_data():
    """Sample outcome data for completed introduction."""
    return {
        "outcome_type": "meeting_scheduled",
        "rating": 5,
        "tags": ["helpful", "valuable"],
        "notes": "Great connection, very helpful",
        "time_to_response_hours": 12.5,
        "time_to_completion_days": 3.2
    }


class TestFeedbackScoreCalculation:
    """Test feedback score calculation logic."""

    def test_requested_stage_returns_neutral(self, rlhf_service):
        """Test that requested stage returns neutral feedback."""
        score = rlhf_service._calculate_feedback_score("requested", None)
        assert score == 0.0

    def test_accepted_stage_returns_positive(self, rlhf_service):
        """Test that accepted stage returns positive feedback."""
        score = rlhf_service._calculate_feedback_score("accepted", None)
        assert score == 0.5

    def test_declined_stage_returns_negative(self, rlhf_service):
        """Test that declined stage returns negative feedback."""
        score = rlhf_service._calculate_feedback_score("declined", None)
        assert score == -0.3

    def test_expired_stage_returns_slight_negative(self, rlhf_service):
        """Test that expired stage returns slight negative feedback."""
        score = rlhf_service._calculate_feedback_score("expired", None)
        assert score == -0.1

    def test_completed_with_high_rating(self, rlhf_service):
        """Test completed stage with 5-star rating."""
        outcome_data = {
            "outcome_type": "meeting_scheduled",
            "rating": 5,
            "tags": ["helpful"],
            "time_to_response_hours": 10,
            "time_to_completion_days": 2
        }
        score = rlhf_service._calculate_feedback_score("completed", outcome_data)

        # Should be high (close to 1.0)
        assert score > 0.8
        assert score <= 1.0

    def test_completed_with_low_rating(self, rlhf_service):
        """Test completed stage with 1-star rating."""
        outcome_data = {
            "outcome_type": "not_relevant",
            "rating": 1,
            "tags": ["not-relevant"],
            "time_to_response_hours": 72,
            "time_to_completion_days": 14
        }
        score = rlhf_service._calculate_feedback_score("completed", outcome_data)

        # Should be low
        assert score < 0.3

    def test_completed_without_rating_uses_outcome_type(self, rlhf_service):
        """Test that outcome type is used when rating is missing."""
        outcome_data = {
            "outcome_type": "meeting_scheduled",
            "time_to_response_hours": 24,
            "time_to_completion_days": 5
        }
        score = rlhf_service._calculate_feedback_score("completed", outcome_data)

        # Should be moderate (based on outcome type)
        assert 0.5 <= score <= 0.9


class TestCompletionScoreCalculation:
    """Test detailed completion score calculation."""

    def test_perfect_completion_score(self, rlhf_service):
        """Test perfect completion scenario."""
        outcome_data = {
            "outcome_type": "meeting_scheduled",
            "rating": 5,
            "tags": ["helpful", "valuable", "great-match"],
            "time_to_response_hours": 6,
            "time_to_completion_days": 2
        }
        score = rlhf_service._calculate_completion_score(outcome_data)

        # Should be very high (> 0.9)
        assert score > 0.9
        assert score <= 1.0

    def test_poor_completion_score(self, rlhf_service):
        """Test poor completion scenario."""
        outcome_data = {
            "outcome_type": "not_relevant",
            "rating": 1,
            "tags": ["bad-match", "spam"],
            "time_to_response_hours": 96,
            "time_to_completion_days": 20
        }
        score = rlhf_service._calculate_completion_score(outcome_data)

        # Should be very low (< 0.2)
        assert score < 0.2

    def test_response_speed_score(self, rlhf_service):
        """Test response speed scoring."""
        # Fast response (< 12 hours)
        fast_score = rlhf_service._calculate_response_speed_score(10)
        assert fast_score == 1.0

        # Moderate response (24 hours)
        moderate_score = rlhf_service._calculate_response_speed_score(24)
        assert moderate_score == 0.8

        # Slow response (72+ hours)
        slow_score = rlhf_service._calculate_response_speed_score(80)
        assert slow_score == 0.2

    def test_completion_speed_score(self, rlhf_service):
        """Test completion speed scoring."""
        # Fast completion (< 3 days)
        fast_score = rlhf_service._calculate_completion_speed_score(2)
        assert fast_score == 1.0

        # Moderate completion (5 days)
        moderate_score = rlhf_service._calculate_completion_speed_score(5)
        assert moderate_score == 0.8

        # Slow completion (14+ days)
        slow_score = rlhf_service._calculate_completion_speed_score(15)
        assert slow_score == 0.2

    def test_tag_sentiment_score(self, rlhf_service):
        """Test tag sentiment scoring."""
        # Positive tags
        positive_score = rlhf_service._calculate_tag_sentiment_score(
            ["helpful", "valuable", "great-match"]
        )
        assert positive_score > 0.8

        # Negative tags
        negative_score = rlhf_service._calculate_tag_sentiment_score(
            ["not-relevant", "bad-match"]
        )
        assert negative_score < 0.3

        # Mixed tags
        mixed_score = rlhf_service._calculate_tag_sentiment_score(
            ["helpful", "timing-off"]
        )
        assert 0.4 <= mixed_score <= 0.6

        # No tags
        no_tags_score = rlhf_service._calculate_tag_sentiment_score([])
        assert no_tags_score == 0.5


class TestPromptAndResponseBuilding:
    """Test prompt and response building for RLHF."""

    def test_build_introduction_prompt(
        self, rlhf_service, sample_match_scores, sample_matching_context
    ):
        """Test introduction prompt building."""
        requester_id = uuid4()
        target_id = uuid4()

        prompt = rlhf_service._build_introduction_prompt(
            requester_id, target_id, sample_match_scores, sample_matching_context
        )

        # Should contain key information
        assert str(requester_id) in prompt
        assert str(target_id) in prompt
        assert "fundraising" in prompt or "hiring" in prompt
        assert "goal_based" in prompt
        assert "Industry match: yes" in prompt

    def test_build_introduction_response(
        self, rlhf_service, sample_match_scores, sample_matching_context
    ):
        """Test introduction response building."""
        response = rlhf_service._build_introduction_response(
            sample_match_scores, sample_matching_context
        )

        # Should contain match scores
        assert "0.81" in response  # overall score
        assert "0.85" in response  # relevance
        assert "0.89" in response  # top similarity

        # Should mention number of matches
        assert "3 matches" in response  # 2 goals + 1 ask


@pytest.mark.asyncio
class TestTrackIntroductionWithContext:
    """Test tracking introduction with full context."""

    @patch('httpx.AsyncClient')
    async def test_track_introduction_requested_stage(
        self, mock_client, rlhf_service, sample_match_scores, sample_matching_context
    ):
        """Test tracking introduction at requested stage."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = {"interaction_id": "test_id_123"}
        mock_response.raise_for_status = Mock()

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        # Call method
        intro_id = uuid4()
        requester_id = uuid4()
        target_id = uuid4()

        interaction_id = await rlhf_service.track_introduction_with_context(
            intro_id=intro_id,
            requester_id=requester_id,
            target_id=target_id,
            match_scores=sample_match_scores,
            matching_context=sample_matching_context,
            stage="requested",
            outcome_data=None
        )

        # Verify
        assert interaction_id == "test_id_123"

        # Verify payload sent to API
        call_args = mock_client_instance.__aenter__.return_value.post.call_args
        payload = call_args[1]["json"]

        assert payload["agent_id"] == "smart_introductions"
        assert payload["feedback"] == 0.0  # Neutral for requested stage
        assert payload["context"]["intro_id"] == str(intro_id)
        assert payload["context"]["match_scores"] == sample_match_scores

    @patch('httpx.AsyncClient')
    async def test_track_introduction_completed_stage(
        self, mock_client, rlhf_service, sample_match_scores,
        sample_matching_context, sample_outcome_data
    ):
        """Test tracking introduction at completed stage."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = {"interaction_id": "test_id_456"}
        mock_response.raise_for_status = Mock()

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        # Call method
        intro_id = uuid4()
        requester_id = uuid4()
        target_id = uuid4()

        interaction_id = await rlhf_service.track_introduction_with_context(
            intro_id=intro_id,
            requester_id=requester_id,
            target_id=target_id,
            match_scores=sample_match_scores,
            matching_context=sample_matching_context,
            stage="completed",
            outcome_data=sample_outcome_data
        )

        # Verify
        assert interaction_id == "test_id_456"

        # Verify payload
        call_args = mock_client_instance.__aenter__.return_value.post.call_args
        payload = call_args[1]["json"]

        assert payload["feedback"] > 0.7  # Should be high for 5-star meeting
        assert payload["context"]["outcome_type"] == "meeting_scheduled"
        assert payload["context"]["rating"] == 5


@pytest.mark.asyncio
class TestMatchingQualityMetrics:
    """Test matching quality metrics retrieval."""

    @patch('httpx.AsyncClient')
    async def test_get_matching_quality_metrics(self, mock_client, rlhf_service):
        """Test getting matching quality metrics."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = {
            "total_interactions": 100,
            "avg_feedback": 0.65,
            "feedback_distribution": {
                "0.0": 10,
                "0.5": 30,
                "1.0": 60
            }
        }
        mock_response.raise_for_status = Mock()

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        # Call method
        metrics = await rlhf_service.get_matching_quality_metrics(time_range="week")

        # Verify
        assert metrics["total_introductions"] == 100
        assert metrics["avg_feedback_score"] == 0.65
        assert metrics["success_rate"] == 0.6  # 60 out of 100 with feedback > 0.6
        assert metrics["response_rate"] == 0.9  # 90 out of 100 with non-zero feedback


@pytest.mark.asyncio
class TestTrainingDatasetExport:
    """Test training dataset export."""

    @patch('httpx.AsyncClient')
    async def test_get_training_dataset(self, mock_client, rlhf_service):
        """Test exporting training dataset."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = {
            "interactions": [
                {
                    "feedback": 0.85,
                    "timestamp": "2025-01-01T12:00:00Z",
                    "context": {
                        "intro_id": "intro_1",
                        "stage": "completed",
                        "match_scores": {
                            "relevance": 0.8,
                            "trust": 0.7,
                            "reciprocity": 0.75,
                            "overall": 0.77
                        },
                        "matching_context": {
                            "goal_matches": ["g1", "g2"],
                            "ask_matches": [],
                            "top_similarity": 0.85,
                            "match_type": "goal_based",
                            "industry_match": True
                        }
                    }
                },
                {
                    "feedback": 0.3,
                    "timestamp": "2025-01-02T12:00:00Z",
                    "context": {
                        "intro_id": "intro_2",
                        "stage": "declined",
                        "match_scores": {
                            "relevance": 0.6,
                            "trust": 0.5,
                            "reciprocity": 0.55,
                            "overall": 0.57
                        },
                        "matching_context": {
                            "goal_matches": [],
                            "ask_matches": ["a1"],
                            "top_similarity": 0.62,
                            "match_type": "ask_based",
                            "industry_match": False
                        }
                    }
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        # Call method
        training_data = await rlhf_service.get_training_dataset(limit=100)

        # Verify
        assert len(training_data) == 2

        # Check first example
        example1 = training_data[0]
        assert example1["relevance_score"] == 0.8
        assert example1["trust_score"] == 0.7
        assert example1["reciprocity_score"] == 0.75
        assert example1["overall_score"] == 0.77
        assert example1["num_goal_matches"] == 2
        assert example1["num_ask_matches"] == 0
        assert example1["top_similarity"] == 0.85
        assert example1["match_type"] == "goal_based"
        assert example1["industry_match"] is True
        assert example1["feedback_score"] == 0.85
        assert example1["success"] is True  # feedback > 0.6

        # Check second example
        example2 = training_data[1]
        assert example2["success"] is False  # feedback < 0.6


@pytest.mark.asyncio
class TestUserSuccessRate:
    """Test user-specific success rate calculation."""

    @patch('httpx.AsyncClient')
    async def test_calculate_success_rate_as_requester(self, mock_client, rlhf_service):
        """Test calculating success rate for user as requester."""
        user_id = uuid4()

        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = {
            "interactions": [
                {"feedback": 0.9, "context": {"requester_id": str(user_id), "target_id": "other_1"}},
                {"feedback": 0.7, "context": {"requester_id": str(user_id), "target_id": "other_2"}},
                {"feedback": 0.4, "context": {"requester_id": str(user_id), "target_id": "other_3"}},
                {"feedback": 0.8, "context": {"requester_id": "other_4", "target_id": str(user_id)}}  # Not counted
            ]
        }
        mock_response.raise_for_status = Mock()

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        # Call method
        result = await rlhf_service.calculate_success_rate(
            user_id=user_id,
            as_requester=True
        )

        # Verify
        assert result["user_id"] == str(user_id)
        assert result["role"] == "requester"
        assert result["total_introductions"] == 3  # Only 3 where user is requester
        assert result["success_count"] == 2  # 2 with feedback > 0.6
        assert result["success_rate"] == 2 / 3  # 66.7%
        assert result["avg_feedback_score"] == (0.9 + 0.7 + 0.4) / 3

    @patch('httpx.AsyncClient')
    async def test_calculate_success_rate_as_target(self, mock_client, rlhf_service):
        """Test calculating success rate for user as target."""
        user_id = uuid4()

        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = {
            "interactions": [
                {"feedback": 0.9, "context": {"requester_id": "other_1", "target_id": str(user_id)}},
                {"feedback": 0.5, "context": {"requester_id": "other_2", "target_id": str(user_id)}},
                {"feedback": 0.8, "context": {"requester_id": str(user_id), "target_id": "other_3"}}  # Not counted
            ]
        }
        mock_response.raise_for_status = Mock()

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        # Call method
        result = await rlhf_service.calculate_success_rate(
            user_id=user_id,
            as_requester=False
        )

        # Verify
        assert result["role"] == "target"
        assert result["total_introductions"] == 2  # Only 2 where user is target
        assert result["success_count"] == 1  # 1 with feedback > 0.6
        assert result["success_rate"] == 0.5  # 50%


class TestFactorImportance:
    """Test factor importance analysis."""

    @pytest.mark.asyncio
    async def test_get_factor_importance_structure(self, rlhf_service):
        """Test that factor importance returns expected structure."""
        result = await rlhf_service.get_factor_importance(time_range="month")

        # Verify structure
        assert "analysis_type" in result
        assert "correlations" in result
        assert "recommended_weights" in result
        assert "confidence" in result

        # Verify correlations exist for all factors
        assert "relevance_score" in result["correlations"]
        assert "trust_score" in result["correlations"]
        assert "reciprocity_score" in result["correlations"]

        # Verify recommended weights sum close to 1.0
        weights = result["recommended_weights"]
        total_weight = weights["relevance"] + weights["trust"] + weights["reciprocity"]
        assert 0.99 <= total_weight <= 1.01  # Allow for rounding


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_calculate_feedback_score_unknown_stage(self, rlhf_service):
        """Test feedback score for unknown stage."""
        score = rlhf_service._calculate_feedback_score("unknown_stage", None)
        assert score == 0.0  # Should default to neutral

    def test_calculate_completion_score_missing_data(self, rlhf_service):
        """Test completion score with minimal data."""
        minimal_outcome = {
            "outcome_type": "email_exchanged"
            # No rating, tags, or timing data
        }
        score = rlhf_service._calculate_completion_score(minimal_outcome)

        # Should still return valid score (using defaults)
        assert 0.0 <= score <= 1.0

    def test_tag_sentiment_with_unknown_tags(self, rlhf_service):
        """Test tag sentiment with tags not in predefined sets."""
        unknown_tags = ["custom-tag-1", "custom-tag-2"]
        score = rlhf_service._calculate_tag_sentiment_score(unknown_tags)

        # Should handle gracefully (default to neutral)
        assert 0.4 <= score <= 0.6


class TestIntegration:
    """Integration tests for RLHF service workflows."""

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_full_introduction_lifecycle(
        self, mock_client, rlhf_service, sample_match_scores, sample_matching_context
    ):
        """Test tracking full introduction lifecycle."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = {"interaction_id": "test_id"}
        mock_response.raise_for_status = Mock()

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        intro_id = uuid4()
        requester_id = uuid4()
        target_id = uuid4()

        # Stage 1: Requested
        await rlhf_service.track_introduction_with_context(
            intro_id=intro_id,
            requester_id=requester_id,
            target_id=target_id,
            match_scores=sample_match_scores,
            matching_context=sample_matching_context,
            stage="requested"
        )

        # Stage 2: Accepted
        await rlhf_service.track_introduction_with_context(
            intro_id=intro_id,
            requester_id=requester_id,
            target_id=target_id,
            match_scores=sample_match_scores,
            matching_context=sample_matching_context,
            stage="accepted"
        )

        # Stage 3: Completed
        await rlhf_service.track_introduction_with_context(
            intro_id=intro_id,
            requester_id=requester_id,
            target_id=target_id,
            match_scores=sample_match_scores,
            matching_context=sample_matching_context,
            stage="completed",
            outcome_data={
                "outcome_type": "meeting_scheduled",
                "rating": 5,
                "tags": ["helpful"],
                "time_to_response_hours": 12,
                "time_to_completion_days": 3
            }
        )

        # Verify all 3 stages were tracked
        assert mock_client_instance.__aenter__.return_value.post.call_count == 3
