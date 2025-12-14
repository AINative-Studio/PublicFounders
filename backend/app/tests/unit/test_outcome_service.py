"""
Unit Tests for Outcome Service

Tests introduction outcome tracking including:
- Outcome recording
- Permission validation
- Outcome updates
- Analytics generation
- RLHF tracking
- Edge cases

Story 8.1: Record Intro Outcome
"""
import pytest
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.outcome_service import (
    OutcomeService,
    OutcomeServiceError
)
from app.schemas.outcome import OutcomeType


@pytest.fixture
def outcome_service():
    """Create outcome service instance."""
    return OutcomeService()


@pytest.fixture
def mock_introduction():
    """Mock introduction data."""
    requester_id = str(uuid4())
    target_id = str(uuid4())
    intro_id = str(uuid4())
    now = datetime.utcnow().isoformat()

    return {
        "id": intro_id,
        "requester_id": requester_id,
        "target_id": target_id,
        "connector_id": None,
        "status": "accepted",
        "requester_message": "Let's connect!",
        "response_message": "Sure!",
        "context": {"shared_goals": ["product_market_fit"]},
        "requested_at": now,
        "responded_at": now,
        "completed_at": None,
        "created_at": now,
        "updated_at": now
    }


@pytest.fixture
def mock_outcome(mock_introduction):
    """Mock outcome data."""
    outcome_id = str(uuid4())
    now = datetime.utcnow().isoformat()

    return {
        "id": outcome_id,
        "introduction_id": mock_introduction["id"],
        "user_id": mock_introduction["requester_id"],
        "outcome_type": OutcomeType.SUCCESSFUL.value,
        "feedback_text": "Great conversation! We're scheduling a follow-up.",
        "rating": 5,
        "tags": ["partnership", "follow-up"],
        "created_at": now,
        "updated_at": now
    }


class TestRecordOutcome:
    """Test recording introduction outcomes."""

    @pytest.mark.asyncio
    async def test_record_outcome_success(
        self,
        outcome_service,
        mock_introduction
    ):
        """Test successful outcome recording."""
        with patch('app.services.outcome_service.zerodb_client') as mock_db, \
             patch('app.services.outcome_service.rlhf_service') as mock_rlhf, \
             patch('app.services.outcome_service.cache_service') as mock_cache:

            # Setup mocks
            mock_db.get_by_id = AsyncMock(return_value=mock_introduction)
            mock_db.query_rows = AsyncMock(return_value=[])  # No existing outcome
            mock_db.insert_rows = AsyncMock(return_value={"success": True})
            mock_rlhf.track_introduction_outcome = AsyncMock(return_value="rlhf_123")
            mock_cache.delete = AsyncMock()

            # Execute
            intro_id = UUID(mock_introduction["id"])
            user_id = UUID(mock_introduction["requester_id"])

            result = await outcome_service.record_outcome(
                intro_id=intro_id,
                user_id=user_id,
                outcome_type=OutcomeType.SUCCESSFUL,
                feedback_text="Great conversation! We're scheduling a follow-up.",
                rating=5,
                tags=["partnership", "follow-up"]
            )

            # Verify
            assert result["introduction_id"] == str(intro_id)
            assert result["user_id"] == str(user_id)
            assert result["outcome_type"] == OutcomeType.SUCCESSFUL.value
            assert result["feedback_text"] == "Great conversation! We're scheduling a follow-up."
            assert result["rating"] == 5
            assert result["tags"] == ["partnership", "follow-up"]
            assert "id" in result
            assert "created_at" in result

            # Verify database insert called
            mock_db.insert_rows.assert_called_once()
            args = mock_db.insert_rows.call_args
            assert args[0][0] == "introduction_outcomes"

            # Verify RLHF tracked
            mock_rlhf.track_introduction_outcome.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_outcome_introduction_not_found(
        self,
        outcome_service
    ):
        """Test recording outcome fails when introduction doesn't exist."""
        with patch('app.services.outcome_service.zerodb_client') as mock_db:
            mock_db.get_by_id = AsyncMock(return_value=None)

            intro_id = uuid4()
            user_id = uuid4()

            with pytest.raises(OutcomeServiceError) as exc_info:
                await outcome_service.record_outcome(
                    intro_id=intro_id,
                    user_id=user_id,
                    outcome_type=OutcomeType.SUCCESSFUL
                )

            assert "Introduction not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_record_outcome_unauthorized_user(
        self,
        outcome_service,
        mock_introduction
    ):
        """Test recording outcome fails for non-participant."""
        with patch('app.services.outcome_service.zerodb_client') as mock_db:
            mock_db.get_by_id = AsyncMock(return_value=mock_introduction)

            intro_id = UUID(mock_introduction["id"])
            unauthorized_user = uuid4()  # Not requester or target

            with pytest.raises(OutcomeServiceError) as exc_info:
                await outcome_service.record_outcome(
                    intro_id=intro_id,
                    user_id=unauthorized_user,
                    outcome_type=OutcomeType.SUCCESSFUL
                )

            assert "Only introduction participants" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_record_outcome_already_exists(
        self,
        outcome_service,
        mock_introduction,
        mock_outcome
    ):
        """Test recording outcome fails if outcome already exists."""
        with patch('app.services.outcome_service.zerodb_client') as mock_db:
            mock_db.get_by_id = AsyncMock(return_value=mock_introduction)
            mock_db.query_rows = AsyncMock(return_value=[mock_outcome])

            intro_id = UUID(mock_introduction["id"])
            user_id = UUID(mock_introduction["requester_id"])

            with pytest.raises(OutcomeServiceError) as exc_info:
                await outcome_service.record_outcome(
                    intro_id=intro_id,
                    user_id=user_id,
                    outcome_type=OutcomeType.SUCCESSFUL
                )

            assert "Outcome already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_record_outcome_target_can_record(
        self,
        outcome_service,
        mock_introduction
    ):
        """Test that target user can also record outcomes."""
        with patch('app.services.outcome_service.zerodb_client') as mock_db, \
             patch('app.services.outcome_service.rlhf_service') as mock_rlhf, \
             patch('app.services.outcome_service.cache_service') as mock_cache:

            mock_db.get_by_id = AsyncMock(return_value=mock_introduction)
            mock_db.query_rows = AsyncMock(return_value=[])
            mock_db.insert_rows = AsyncMock(return_value={"success": True})
            mock_rlhf.track_introduction_outcome = AsyncMock()
            mock_cache.delete = AsyncMock()

            intro_id = UUID(mock_introduction["id"])
            target_user_id = UUID(mock_introduction["target_id"])

            result = await outcome_service.record_outcome(
                intro_id=intro_id,
                user_id=target_user_id,
                outcome_type=OutcomeType.UNSUCCESSFUL,
                feedback_text="Not a good fit for us at this time."
            )

            assert result["user_id"] == str(target_user_id)
            assert result["outcome_type"] == OutcomeType.UNSUCCESSFUL.value

    @pytest.mark.asyncio
    async def test_record_outcome_minimal_data(
        self,
        outcome_service,
        mock_introduction
    ):
        """Test recording outcome with only required fields."""
        with patch('app.services.outcome_service.zerodb_client') as mock_db, \
             patch('app.services.outcome_service.rlhf_service') as mock_rlhf, \
             patch('app.services.outcome_service.cache_service') as mock_cache:

            mock_db.get_by_id = AsyncMock(return_value=mock_introduction)
            mock_db.query_rows = AsyncMock(return_value=[])
            mock_db.insert_rows = AsyncMock(return_value={"success": True})
            mock_rlhf.track_introduction_outcome = AsyncMock()
            mock_cache.delete = AsyncMock()

            intro_id = UUID(mock_introduction["id"])
            user_id = UUID(mock_introduction["requester_id"])

            result = await outcome_service.record_outcome(
                intro_id=intro_id,
                user_id=user_id,
                outcome_type=OutcomeType.NO_RESPONSE
            )

            assert result["outcome_type"] == OutcomeType.NO_RESPONSE.value
            assert result["feedback_text"] is None
            assert result["rating"] is None
            assert result["tags"] == []


class TestGetOutcome:
    """Test retrieving outcomes."""

    @pytest.mark.asyncio
    async def test_get_outcome_success(
        self,
        outcome_service,
        mock_outcome
    ):
        """Test successful outcome retrieval."""
        with patch('app.services.outcome_service.cache_service') as mock_cache, \
             patch('app.services.outcome_service.zerodb_client') as mock_db:

            mock_cache.get = AsyncMock(return_value=None)  # Cache miss
            mock_db.query_rows = AsyncMock(return_value=[mock_outcome])
            mock_cache.set = AsyncMock()

            intro_id = UUID(mock_outcome["introduction_id"])
            result = await outcome_service.get_outcome(intro_id)

            assert result is not None
            assert result["id"] == mock_outcome["id"]
            assert result["outcome_type"] == mock_outcome["outcome_type"]

            # Verify caching
            mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_outcome_not_found(
        self,
        outcome_service
    ):
        """Test getting outcome returns None when not found."""
        with patch('app.services.outcome_service.cache_service') as mock_cache, \
             patch('app.services.outcome_service.zerodb_client') as mock_db:

            mock_cache.get = AsyncMock(return_value=None)
            mock_db.query_rows = AsyncMock(return_value=[])

            intro_id = uuid4()
            result = await outcome_service.get_outcome(intro_id)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_outcome_from_cache(
        self,
        outcome_service,
        mock_outcome
    ):
        """Test getting outcome from cache."""
        with patch('app.services.outcome_service.cache_service') as mock_cache, \
             patch('app.services.outcome_service.zerodb_client') as mock_db:

            mock_cache.get = AsyncMock(return_value=mock_outcome)

            intro_id = UUID(mock_outcome["introduction_id"])
            result = await outcome_service.get_outcome(intro_id)

            assert result == mock_outcome
            # Verify database not queried
            mock_db.query_rows.assert_not_called()


class TestUpdateOutcome:
    """Test updating outcomes."""

    @pytest.mark.asyncio
    async def test_update_outcome_success(
        self,
        outcome_service,
        mock_introduction,
        mock_outcome
    ):
        """Test successful outcome update."""
        with patch('app.services.outcome_service.zerodb_client') as mock_db, \
             patch('app.services.outcome_service.cache_service') as mock_cache, \
             patch('app.services.outcome_service.rlhf_service') as mock_rlhf:

            # Mock get_outcome to return existing outcome
            with patch.object(
                outcome_service,
                'get_outcome',
                AsyncMock(return_value=mock_outcome)
            ):
                mock_db.get_by_id = AsyncMock(return_value=mock_introduction)
                updated_outcome = {**mock_outcome, "rating": 4}
                mock_db.update_rows = AsyncMock(return_value={"success": True})
                mock_db.query_rows = AsyncMock(return_value=[updated_outcome])
                mock_cache.delete = AsyncMock()
                mock_rlhf.track_introduction_outcome = AsyncMock()

                intro_id = UUID(mock_introduction["id"])
                user_id = UUID(mock_introduction["requester_id"])

                result = await outcome_service.update_outcome(
                    intro_id=intro_id,
                    user_id=user_id,
                    rating=4
                )

                assert result["rating"] == 4
                mock_db.update_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_outcome_not_found(
        self,
        outcome_service,
        mock_introduction
    ):
        """Test updating non-existent outcome fails."""
        with patch('app.services.outcome_service.zerodb_client') as mock_db:
            # Mock get_outcome to return None
            with patch.object(
                outcome_service,
                'get_outcome',
                AsyncMock(return_value=None)
            ):
                mock_db.get_by_id = AsyncMock(return_value=mock_introduction)

                intro_id = UUID(mock_introduction["id"])
                user_id = UUID(mock_introduction["requester_id"])

                with pytest.raises(OutcomeServiceError) as exc_info:
                    await outcome_service.update_outcome(
                        intro_id=intro_id,
                        user_id=user_id,
                        rating=4
                    )

                assert "Outcome not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_outcome_unauthorized(
        self,
        outcome_service,
        mock_introduction,
        mock_outcome
    ):
        """Test updating outcome fails for non-participant."""
        with patch('app.services.outcome_service.zerodb_client') as mock_db:
            with patch.object(
                outcome_service,
                'get_outcome',
                AsyncMock(return_value=mock_outcome)
            ):
                mock_db.get_by_id = AsyncMock(return_value=mock_introduction)

                intro_id = UUID(mock_introduction["id"])
                unauthorized_user = uuid4()

                with pytest.raises(OutcomeServiceError) as exc_info:
                    await outcome_service.update_outcome(
                        intro_id=intro_id,
                        user_id=unauthorized_user,
                        rating=4
                    )

                assert "Only introduction participants" in str(exc_info.value)


class TestGetOutcomeAnalytics:
    """Test analytics generation."""

    @pytest.mark.asyncio
    async def test_get_analytics_with_outcomes(
        self,
        outcome_service
    ):
        """Test analytics generation with outcome data."""
        user_id = uuid4()
        outcomes = [
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "outcome_type": OutcomeType.SUCCESSFUL.value,
                "rating": 5,
                "tags": ["partnership", "valuable"],
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "outcome_type": OutcomeType.SUCCESSFUL.value,
                "rating": 4,
                "tags": ["follow-up", "valuable"],
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "outcome_type": OutcomeType.UNSUCCESSFUL.value,
                "rating": 3,
                "tags": ["not-actionable"],
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "outcome_type": OutcomeType.NO_RESPONSE.value,
                "rating": None,
                "tags": [],
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        with patch('app.services.outcome_service.zerodb_client') as mock_db:
            mock_db.query_rows = AsyncMock(return_value=outcomes)

            result = await outcome_service.get_outcome_analytics(user_id)

            # Verify basic stats
            assert result["user_id"] == str(user_id)
            assert result["total_outcomes"] == 4

            # Verify success rate (2/4 = 50%)
            assert result["success_rate"] == 50.0

            # Verify response rate ((2+1)/4 = 75%)
            assert result["response_rate"] == 75.0

            # Verify average rating (5+4+3)/3 = 4.0
            assert result["average_rating"] == 4.0

            # Verify breakdown
            assert len(result["outcome_breakdown"]) == 4
            successful_breakdown = next(
                b for b in result["outcome_breakdown"]
                if b["outcome_type"] == OutcomeType.SUCCESSFUL.value
            )
            assert successful_breakdown["count"] == 2
            assert successful_breakdown["percentage"] == 50.0

            # Verify top tags
            assert len(result["top_tags"]) > 0
            assert result["top_tags"][0]["tag"] == "valuable"
            assert result["top_tags"][0]["count"] == 2

    @pytest.mark.asyncio
    async def test_get_analytics_no_outcomes(
        self,
        outcome_service
    ):
        """Test analytics generation with no outcomes."""
        user_id = uuid4()

        with patch('app.services.outcome_service.zerodb_client') as mock_db:
            mock_db.query_rows = AsyncMock(return_value=[])

            result = await outcome_service.get_outcome_analytics(user_id)

            assert result["total_outcomes"] == 0
            assert result["success_rate"] == 0.0
            assert result["response_rate"] == 0.0
            assert result["average_rating"] is None
            assert len(result["outcome_breakdown"]) == 4
            assert len(result["top_tags"]) == 0

    @pytest.mark.asyncio
    async def test_get_analytics_with_date_range(
        self,
        outcome_service
    ):
        """Test analytics with date filtering."""
        user_id = uuid4()
        period_start = datetime.utcnow() - timedelta(days=30)
        period_end = datetime.utcnow()

        with patch('app.services.outcome_service.zerodb_client') as mock_db:
            mock_db.query_rows = AsyncMock(return_value=[])

            result = await outcome_service.get_outcome_analytics(
                user_id,
                period_start=period_start,
                period_end=period_end
            )

            # Verify date range in filter
            call_args = mock_db.query_rows.call_args
            filter_query = call_args[1]["filter"]
            assert "created_at" in filter_query
            assert "$gte" in filter_query["created_at"]
            assert "$lte" in filter_query["created_at"]


class TestRLHFTracking:
    """Test RLHF integration."""

    @pytest.mark.asyncio
    async def test_rlhf_tracking_successful_outcome(
        self,
        outcome_service,
        mock_introduction
    ):
        """Test RLHF tracking for successful outcome with high rating."""
        with patch('app.services.outcome_service.rlhf_service') as mock_rlhf:
            mock_rlhf.track_introduction_outcome = AsyncMock()

            await outcome_service._track_rlhf(
                intro_id=UUID(mock_introduction["id"]),
                introduction=mock_introduction,
                outcome_type=OutcomeType.SUCCESSFUL,
                rating=5,
                feedback_text="Excellent connection!"
            )

            # Verify RLHF called with positive score
            call_args = mock_rlhf.track_introduction_outcome.call_args
            assert call_args[1]["outcome"] == OutcomeType.SUCCESSFUL.value
            # Successful + rating 5 should give high positive score
            assert call_args[1]["value_score"] > 0.5

    @pytest.mark.asyncio
    async def test_rlhf_tracking_unsuccessful_outcome(
        self,
        outcome_service,
        mock_introduction
    ):
        """Test RLHF tracking for unsuccessful outcome."""
        with patch('app.services.outcome_service.rlhf_service') as mock_rlhf:
            mock_rlhf.track_introduction_outcome = AsyncMock()

            await outcome_service._track_rlhf(
                intro_id=UUID(mock_introduction["id"]),
                introduction=mock_introduction,
                outcome_type=OutcomeType.UNSUCCESSFUL,
                rating=3,
                feedback_text="Not a good fit."
            )

            call_args = mock_rlhf.track_introduction_outcome.call_args
            assert call_args[1]["outcome"] == OutcomeType.UNSUCCESSFUL.value
            # Unsuccessful should give neutral to slightly positive score
            assert -0.5 < call_args[1]["value_score"] < 0.5

    @pytest.mark.asyncio
    async def test_rlhf_tracking_no_response(
        self,
        outcome_service,
        mock_introduction
    ):
        """Test RLHF tracking for no response outcome."""
        with patch('app.services.outcome_service.rlhf_service') as mock_rlhf:
            mock_rlhf.track_introduction_outcome = AsyncMock()

            await outcome_service._track_rlhf(
                intro_id=UUID(mock_introduction["id"]),
                introduction=mock_introduction,
                outcome_type=OutcomeType.NO_RESPONSE,
                rating=None,
                feedback_text=None
            )

            call_args = mock_rlhf.track_introduction_outcome.call_args
            assert call_args[1]["outcome"] == OutcomeType.NO_RESPONSE.value
            # No response should give negative score
            assert call_args[1]["value_score"] < 0
