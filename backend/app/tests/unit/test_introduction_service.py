"""
Unit Tests for Introduction Service

Tests introduction lifecycle management including:
- Request creation
- Response handling (accept/decline)
- Completion tracking
- Expiration handling
- Permission validation
- Edge cases
"""
import pytest
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.introduction_service import (
    IntroductionService,
    IntroductionStatus,
    IntroductionOutcome,
    IntroductionServiceError
)


@pytest.fixture
def introduction_service():
    """Create introduction service instance."""
    return IntroductionService()


@pytest.fixture
def mock_requester():
    """Mock requester user."""
    return {
        "id": str(uuid4()),
        "email": "requester@example.com",
        "name": "Alice Founder"
    }


@pytest.fixture
def mock_target():
    """Mock target user."""
    return {
        "id": str(uuid4()),
        "email": "target@example.com",
        "name": "Bob Founder"
    }


@pytest.fixture
def mock_connector():
    """Mock connector user."""
    return {
        "id": str(uuid4()),
        "email": "connector@example.com",
        "name": "Charlie Connector"
    }


@pytest.fixture
def mock_introduction(mock_requester, mock_target):
    """Mock introduction data."""
    intro_id = str(uuid4())
    now = datetime.utcnow().isoformat()
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()

    return {
        "id": intro_id,
        "requester_id": mock_requester["id"],
        "target_id": mock_target["id"],
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
        "embedding_id": "intro_embed_123",
        "created_at": now,
        "updated_at": now
    }


class TestRequestIntroduction:
    """Test introduction request creation."""

    @pytest.mark.asyncio
    async def test_request_introduction_success(
        self,
        introduction_service,
        mock_requester,
        mock_target
    ):
        """Test successful introduction request."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db, \
             patch('app.services.introduction_service.embedding_service') as mock_embed, \
             patch('app.services.introduction_service.rlhf_service') as mock_rlhf, \
             patch('app.services.introduction_service.cache_service') as mock_cache:

            # Setup mocks
            mock_db.get_by_id = AsyncMock(side_effect=[
                mock_requester,  # First call returns requester
                mock_target       # Second call returns target
            ])
            mock_db.query_rows = AsyncMock(return_value=[])
            mock_db.insert_rows = AsyncMock(return_value={"success": True})

            mock_embed.upsert_embedding = AsyncMock(return_value="embed_123")
            mock_rlhf.track_introduction_outcome = AsyncMock(return_value="rlhf_123")
            mock_cache.delete_pattern = AsyncMock()

            # Execute
            result = await introduction_service.request_introduction(
                requester_id=UUID(mock_requester["id"]),
                target_id=UUID(mock_target["id"]),
                message="I'd love to connect about SaaS scaling.",
                context={"reason": "complementary_expertise"}
            )

            # Verify
            assert result["requester_id"] == mock_requester["id"]
            assert result["target_id"] == mock_target["id"]
            assert result["status"] == IntroductionStatus.PENDING.value
            assert result["requester_message"] == "I'd love to connect about SaaS scaling."
            assert "id" in result
            assert "expires_at" in result

            # Verify database insert called
            mock_db.insert_rows.assert_called_once()
            args = mock_db.insert_rows.call_args
            assert args[0][0] == "introductions"

            # Verify embedding created
            mock_embed.upsert_embedding.assert_called_once()

            # Verify RLHF tracked
            mock_rlhf.track_introduction_outcome.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_introduction_requester_not_found(
        self,
        introduction_service,
        mock_target
    ):
        """Test request fails when requester doesn't exist."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db:
            mock_db.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(IntroductionServiceError, match="Requester user not found"):
                await introduction_service.request_introduction(
                    requester_id=uuid4(),
                    target_id=UUID(mock_target["id"]),
                    message="Test message"
                )

    @pytest.mark.asyncio
    async def test_request_introduction_target_not_found(
        self,
        introduction_service,
        mock_requester
    ):
        """Test request fails when target doesn't exist."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db:
            mock_db.get_by_id = AsyncMock(side_effect=[
                mock_requester,  # Requester exists
                None             # Target doesn't exist
            ])

            with pytest.raises(IntroductionServiceError, match="Target user not found"):
                await introduction_service.request_introduction(
                    requester_id=UUID(mock_requester["id"]),
                    target_id=uuid4(),
                    message="Test message"
                )

    @pytest.mark.asyncio
    async def test_request_introduction_self(
        self,
        introduction_service,
        mock_requester
    ):
        """Test cannot request introduction to yourself."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db:
            mock_db.get_by_id = AsyncMock(return_value=mock_requester)

            user_id = UUID(mock_requester["id"])

            with pytest.raises(IntroductionServiceError, match="Cannot request introduction to yourself"):
                await introduction_service.request_introduction(
                    requester_id=user_id,
                    target_id=user_id,
                    message="Test message"
                )

    @pytest.mark.asyncio
    async def test_request_introduction_already_exists(
        self,
        introduction_service,
        mock_requester,
        mock_target,
        mock_introduction
    ):
        """Test request fails when introduction already exists."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db:
            mock_db.get_by_id = AsyncMock(side_effect=[
                mock_requester,
                mock_target
            ])
            mock_db.query_rows = AsyncMock(return_value=[mock_introduction])

            with pytest.raises(IntroductionServiceError, match="Introduction already exists"):
                await introduction_service.request_introduction(
                    requester_id=UUID(mock_requester["id"]),
                    target_id=UUID(mock_target["id"]),
                    message="Test message"
                )

    @pytest.mark.asyncio
    async def test_request_introduction_with_connector(
        self,
        introduction_service,
        mock_requester,
        mock_target,
        mock_connector
    ):
        """Test introduction request with connector."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db, \
             patch('app.services.introduction_service.embedding_service') as mock_embed, \
             patch('app.services.introduction_service.rlhf_service') as mock_rlhf, \
             patch('app.services.introduction_service.cache_service') as mock_cache:

            mock_db.get_by_id = AsyncMock(side_effect=[
                mock_requester,
                mock_target,
                mock_connector
            ])
            mock_db.query_rows = AsyncMock(return_value=[])
            mock_db.insert_rows = AsyncMock(return_value={"success": True})
            mock_embed.upsert_embedding = AsyncMock(return_value="embed_123")
            mock_rlhf.track_introduction_outcome = AsyncMock(return_value="rlhf_123")
            mock_cache.delete_pattern = AsyncMock()

            result = await introduction_service.request_introduction(
                requester_id=UUID(mock_requester["id"]),
                target_id=UUID(mock_target["id"]),
                message="Test message",
                connector_id=UUID(mock_connector["id"])
            )

            assert result["connector_id"] == mock_connector["id"]


class TestRespondToIntroduction:
    """Test introduction response handling."""

    @pytest.mark.asyncio
    async def test_accept_introduction(
        self,
        introduction_service,
        mock_introduction,
        mock_target
    ):
        """Test accepting an introduction."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db, \
             patch('app.services.introduction_service.rlhf_service') as mock_rlhf, \
             patch('app.services.introduction_service.cache_service') as mock_cache:

            mock_db.get_by_id = AsyncMock(side_effect=[
                mock_introduction,
                {**mock_introduction, "status": IntroductionStatus.ACCEPTED.value}
            ])
            mock_db.update_rows = AsyncMock(return_value={"success": True})
            mock_rlhf.track_introduction_outcome = AsyncMock()
            mock_cache.delete_pattern = AsyncMock()

            result = await introduction_service.respond_to_introduction(
                intro_id=UUID(mock_introduction["id"]),
                user_id=UUID(mock_target["id"]),
                accept=True,
                message="Happy to connect!"
            )

            assert result["status"] == IntroductionStatus.ACCEPTED.value

            # Verify update called
            mock_db.update_rows.assert_called_once()

            # Verify RLHF tracked with positive score
            mock_rlhf.track_introduction_outcome.assert_called_once()
            call_args = mock_rlhf.track_introduction_outcome.call_args
            assert call_args[1]["value_score"] == 1.0

    @pytest.mark.asyncio
    async def test_decline_introduction(
        self,
        introduction_service,
        mock_introduction,
        mock_target
    ):
        """Test declining an introduction."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db, \
             patch('app.services.introduction_service.rlhf_service') as mock_rlhf, \
             patch('app.services.introduction_service.cache_service') as mock_cache:

            mock_db.get_by_id = AsyncMock(side_effect=[
                mock_introduction,
                {**mock_introduction, "status": IntroductionStatus.DECLINED.value}
            ])
            mock_db.update_rows = AsyncMock(return_value={"success": True})
            mock_rlhf.track_introduction_outcome = AsyncMock()
            mock_cache.delete_pattern = AsyncMock()

            result = await introduction_service.respond_to_introduction(
                intro_id=UUID(mock_introduction["id"]),
                user_id=UUID(mock_target["id"]),
                accept=False,
                message="Not at this time, thanks."
            )

            assert result["status"] == IntroductionStatus.DECLINED.value

            # Verify RLHF tracked with negative score
            call_args = mock_rlhf.track_introduction_outcome.call_args
            assert call_args[1]["value_score"] == -0.5

    @pytest.mark.asyncio
    async def test_respond_not_target(
        self,
        introduction_service,
        mock_introduction
    ):
        """Test only target can respond."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db:
            mock_db.get_by_id = AsyncMock(return_value=mock_introduction)

            wrong_user_id = uuid4()

            with pytest.raises(IntroductionServiceError, match="Only the target can respond"):
                await introduction_service.respond_to_introduction(
                    intro_id=UUID(mock_introduction["id"]),
                    user_id=wrong_user_id,
                    accept=True
                )

    @pytest.mark.asyncio
    async def test_respond_already_responded(
        self,
        introduction_service,
        mock_introduction,
        mock_target
    ):
        """Test cannot respond to already responded introduction."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db:
            responded_intro = {
                **mock_introduction,
                "status": IntroductionStatus.ACCEPTED.value
            }
            mock_db.get_by_id = AsyncMock(return_value=responded_intro)

            with pytest.raises(IntroductionServiceError, match="already accepted"):
                await introduction_service.respond_to_introduction(
                    intro_id=UUID(mock_introduction["id"]),
                    user_id=UUID(mock_target["id"]),
                    accept=True
                )

    @pytest.mark.asyncio
    async def test_respond_expired(
        self,
        introduction_service,
        mock_introduction,
        mock_target
    ):
        """Test cannot respond to expired introduction."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db:
            # Set expiry to past
            expired_intro = {
                **mock_introduction,
                "expires_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
            }
            mock_db.get_by_id = AsyncMock(return_value=expired_intro)
            mock_db.update_rows = AsyncMock()

            with pytest.raises(IntroductionServiceError, match="has expired"):
                await introduction_service.respond_to_introduction(
                    intro_id=UUID(mock_introduction["id"]),
                    user_id=UUID(mock_target["id"]),
                    accept=True
                )


class TestCompleteIntroduction:
    """Test introduction completion."""

    @pytest.mark.asyncio
    async def test_complete_introduction_meeting_scheduled(
        self,
        introduction_service,
        mock_introduction,
        mock_requester
    ):
        """Test completing introduction with successful outcome."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db, \
             patch('app.services.introduction_service.rlhf_service') as mock_rlhf, \
             patch('app.services.introduction_service.cache_service') as mock_cache:

            accepted_intro = {
                **mock_introduction,
                "status": IntroductionStatus.ACCEPTED.value
            }

            mock_db.get_by_id = AsyncMock(side_effect=[
                accepted_intro,
                {**accepted_intro, "status": IntroductionStatus.COMPLETED.value}
            ])
            mock_db.update_rows = AsyncMock()
            mock_rlhf.track_introduction_outcome = AsyncMock()
            mock_cache.delete_pattern = AsyncMock()

            result = await introduction_service.complete_introduction(
                intro_id=UUID(mock_introduction["id"]),
                user_id=UUID(mock_requester["id"]),
                outcome=IntroductionOutcome.MEETING_SCHEDULED,
                notes="Great call scheduled for next week!"
            )

            assert result["status"] == IntroductionStatus.COMPLETED.value

            # Verify RLHF tracked with high success score
            call_args = mock_rlhf.track_introduction_outcome.call_args
            assert call_args[1]["value_score"] == 1.0

    @pytest.mark.asyncio
    async def test_complete_introduction_no_response(
        self,
        introduction_service,
        mock_introduction,
        mock_requester
    ):
        """Test completing with no_response outcome."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db, \
             patch('app.services.introduction_service.rlhf_service') as mock_rlhf, \
             patch('app.services.introduction_service.cache_service') as mock_cache:

            accepted_intro = {
                **mock_introduction,
                "status": IntroductionStatus.ACCEPTED.value
            }

            mock_db.get_by_id = AsyncMock(side_effect=[
                accepted_intro,
                {**accepted_intro, "status": IntroductionStatus.COMPLETED.value}
            ])
            mock_db.update_rows = AsyncMock()
            mock_rlhf.track_introduction_outcome = AsyncMock()
            mock_cache.delete_pattern = AsyncMock()

            result = await introduction_service.complete_introduction(
                intro_id=UUID(mock_introduction["id"]),
                user_id=UUID(mock_requester["id"]),
                outcome=IntroductionOutcome.NO_RESPONSE
            )

            # Verify lower score for unsuccessful outcome
            call_args = mock_rlhf.track_introduction_outcome.call_args
            assert call_args[1]["value_score"] == 0.3

    @pytest.mark.asyncio
    async def test_complete_not_authorized(
        self,
        introduction_service,
        mock_introduction
    ):
        """Test only involved users can complete."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db:
            mock_db.get_by_id = AsyncMock(return_value=mock_introduction)

            wrong_user_id = uuid4()

            with pytest.raises(IntroductionServiceError, match="Not authorized"):
                await introduction_service.complete_introduction(
                    intro_id=UUID(mock_introduction["id"]),
                    user_id=wrong_user_id,
                    outcome=IntroductionOutcome.MEETING_SCHEDULED
                )


class TestGetIntroductions:
    """Test fetching introduction lists."""

    @pytest.mark.asyncio
    async def test_get_received_introductions(
        self,
        introduction_service,
        mock_target,
        mock_introduction
    ):
        """Test getting received introductions."""
        with patch('app.services.introduction_service.cache_service') as mock_cache, \
             patch('app.services.introduction_service.zerodb_client') as mock_db:

            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_db.query_rows = AsyncMock(return_value=[mock_introduction])

            result = await introduction_service.get_received_introductions(
                user_id=UUID(mock_target["id"]),
                limit=20,
                offset=0
            )

            assert len(result) == 1
            assert result[0]["id"] == mock_introduction["id"]

    @pytest.mark.asyncio
    async def test_get_sent_introductions(
        self,
        introduction_service,
        mock_requester,
        mock_introduction
    ):
        """Test getting sent introductions."""
        with patch('app.services.introduction_service.cache_service') as mock_cache, \
             patch('app.services.introduction_service.zerodb_client') as mock_db:

            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_db.query_rows = AsyncMock(return_value=[mock_introduction])

            result = await introduction_service.get_sent_introductions(
                user_id=UUID(mock_requester["id"]),
                limit=20,
                offset=0
            )

            assert len(result) == 1
            assert result[0]["id"] == mock_introduction["id"]


class TestExpireIntroductions:
    """Test introduction expiration."""

    @pytest.mark.asyncio
    async def test_expire_old_introductions(
        self,
        introduction_service,
        mock_introduction
    ):
        """Test expiring old pending introductions."""
        with patch('app.services.introduction_service.zerodb_client') as mock_db:
            # Create expired introduction
            expired_intro = {
                **mock_introduction,
                "expires_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
            }

            mock_db.query_rows = AsyncMock(return_value=[expired_intro])
            mock_db.update_rows = AsyncMock()

            count = await introduction_service.expire_old_introductions()

            assert count == 1
            mock_db.update_rows.assert_called_once()

            # Verify status updated to expired
            call_args = mock_db.update_rows.call_args
            assert call_args[1]["update"]["$set"]["status"] == IntroductionStatus.EXPIRED.value
