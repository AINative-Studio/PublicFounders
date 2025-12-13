"""
Introduction Service - Manages founder connection requests and executions.

This service handles:
1. Introduction request creation
2. Response handling (accept/decline)
3. Introduction completion tracking
4. RLHF outcome tracking for learning
5. Expiration management

Architecture:
- ZeroDB for NoSQL storage
- Embedding service for message context
- RLHF service for outcome tracking
- Cache service for performance optimization
"""
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional
from uuid import UUID

from app.services.zerodb_client import zerodb_client
from app.services.embedding_service import embedding_service
from app.services.rlhf_service import rlhf_service
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


class IntroductionStatus(str, Enum):
    """Introduction lifecycle status."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    COMPLETED = "completed"
    EXPIRED = "expired"


class IntroductionOutcome(str, Enum):
    """Introduction completion outcomes."""
    MEETING_SCHEDULED = "meeting_scheduled"
    EMAIL_EXCHANGED = "email_exchanged"
    NO_RESPONSE = "no_response"
    NOT_RELEVANT = "not_relevant"


class IntroductionServiceError(Exception):
    """Base exception for introduction service errors."""
    pass


class IntroductionService:
    """
    Manages introduction request lifecycle and tracking.

    Key Features:
    - Request validation and creation
    - Status tracking throughout lifecycle
    - RLHF outcome tracking for learning
    - Automatic expiration handling
    - Permission validation
    """

    INTRODUCTION_EXPIRY_DAYS = 7
    CACHE_TTL = 300  # 5 minutes

    def __init__(self):
        """Initialize introduction service."""
        self.table_name = "introductions"

    async def request_introduction(
        self,
        requester_id: UUID,
        target_id: UUID,
        message: str,
        connector_id: Optional[UUID] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create an introduction request.

        Args:
            requester_id: User requesting the introduction
            target_id: User being introduced to
            message: Personalized introduction message
            connector_id: Optional mutual connection facilitating intro
            context: Optional additional context

        Returns:
            Created introduction object

        Raises:
            IntroductionServiceError: If validation fails or creation errors
        """
        logger.info(
            f"Creating introduction request from {requester_id} to {target_id}"
        )

        try:
            # Validate users exist
            requester = await zerodb_client.get_by_id("users", str(requester_id))
            target = await zerodb_client.get_by_id("users", str(target_id))

            if not requester:
                raise IntroductionServiceError("Requester user not found")
            if not target:
                raise IntroductionServiceError("Target user not found")

            # Prevent self-introductions
            if requester_id == target_id:
                raise IntroductionServiceError("Cannot request introduction to yourself")

            # Check if introduction already exists
            existing = await self.check_existing_introduction(requester_id, target_id)
            if existing:
                status = existing.get("status")
                raise IntroductionServiceError(
                    f"Introduction already exists with status: {status}"
                )

            # Validate connector if provided
            if connector_id:
                connector = await zerodb_client.get_by_id("users", str(connector_id))
                if not connector:
                    raise IntroductionServiceError("Connector user not found")

            # Generate unique ID
            from uuid import uuid4
            intro_id = str(uuid4())

            # Calculate timestamps
            now = datetime.utcnow().isoformat()
            expires_at = (
                datetime.utcnow() + timedelta(days=self.INTRODUCTION_EXPIRY_DAYS)
            ).isoformat()

            # Generate embedding for message context
            try:
                embedding_content = f"Introduction request: {message}"
                embedding_id = await embedding_service.upsert_embedding(
                    entity_type="introduction",
                    entity_id=UUID(intro_id),
                    content=embedding_content,
                    metadata={
                        "requester_id": str(requester_id),
                        "target_id": str(target_id),
                        "has_connector": connector_id is not None
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to create embedding: {e}")
                embedding_id = None

            # Prepare introduction data
            intro_data = {
                "id": intro_id,
                "requester_id": str(requester_id),
                "target_id": str(target_id),
                "connector_id": str(connector_id) if connector_id else None,
                "status": IntroductionStatus.PENDING.value,
                "requester_message": message,
                "response_message": None,
                "context": context or {},
                "requested_at": now,
                "responded_at": None,
                "completed_at": None,
                "expires_at": expires_at,
                "outcome": None,
                "outcome_notes": None,
                "embedding_id": embedding_id,
                "created_at": now,
                "updated_at": now
            }

            # Insert into database
            await zerodb_client.insert_rows(self.table_name, [intro_data])

            logger.info(f"Created introduction {intro_id}")

            # Track in RLHF (neutral feedback initially)
            try:
                await rlhf_service.track_introduction_outcome(
                    intro_id=UUID(intro_id),
                    from_user_id=requester_id,
                    to_user_id=target_id,
                    outcome="requested",
                    value_score=0.0  # Neutral - will update on response
                )
            except Exception as e:
                logger.warning(f"Failed to track RLHF: {e}")

            # Invalidate relevant caches
            await self._invalidate_user_caches(requester_id, target_id)

            return intro_data

        except IntroductionServiceError:
            raise
        except Exception as e:
            logger.error(f"Error creating introduction: {e}")
            raise IntroductionServiceError(f"Failed to create introduction: {e}")

    async def respond_to_introduction(
        self,
        intro_id: UUID,
        user_id: UUID,
        accept: bool,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Accept or decline an introduction request.

        Args:
            intro_id: Introduction ID
            user_id: User responding (must be target)
            accept: True to accept, False to decline
            message: Optional response message

        Returns:
            Updated introduction object

        Raises:
            IntroductionServiceError: If validation fails or update errors
        """
        logger.info(
            f"Processing introduction response {intro_id} from {user_id}: "
            f"{'accept' if accept else 'decline'}"
        )

        try:
            # Fetch introduction
            intro = await zerodb_client.get_by_id(self.table_name, str(intro_id))
            if not intro:
                raise IntroductionServiceError("Introduction not found")

            # Verify user is the target
            if intro["target_id"] != str(user_id):
                raise IntroductionServiceError(
                    "Only the target can respond to this introduction"
                )

            # Check current status
            current_status = intro["status"]
            if current_status != IntroductionStatus.PENDING.value:
                raise IntroductionServiceError(
                    f"Introduction already {current_status}, cannot respond"
                )

            # Check not expired
            expires_at = datetime.fromisoformat(intro["expires_at"])
            if datetime.utcnow() > expires_at:
                # Mark as expired
                await self._expire_introduction(intro_id)
                raise IntroductionServiceError("Introduction has expired")

            # Determine new status
            new_status = (
                IntroductionStatus.ACCEPTED if accept
                else IntroductionStatus.DECLINED
            )
            now = datetime.utcnow().isoformat()

            # Update introduction
            update_data = {
                "status": new_status.value,
                "response_message": message,
                "responded_at": now,
                "updated_at": now
            }

            await zerodb_client.update_rows(
                self.table_name,
                filter={"id": str(intro_id)},
                update={"$set": update_data}
            )

            logger.info(
                f"Updated introduction {intro_id} status to {new_status.value}"
            )

            # Track outcome in RLHF
            try:
                value_score = 1.0 if accept else -0.5
                await rlhf_service.track_introduction_outcome(
                    intro_id=intro_id,
                    from_user_id=UUID(intro["requester_id"]),
                    to_user_id=user_id,
                    outcome="accepted" if accept else "declined",
                    value_score=value_score
                )
            except Exception as e:
                logger.warning(f"Failed to track RLHF outcome: {e}")

            # Invalidate caches
            await self._invalidate_user_caches(
                UUID(intro["requester_id"]), user_id
            )

            # Get updated introduction
            updated_intro = await zerodb_client.get_by_id(
                self.table_name, str(intro_id)
            )

            return updated_intro

        except IntroductionServiceError:
            raise
        except Exception as e:
            logger.error(f"Error responding to introduction: {e}")
            raise IntroductionServiceError(f"Failed to respond: {e}")

    async def complete_introduction(
        self,
        intro_id: UUID,
        user_id: UUID,
        outcome: IntroductionOutcome,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark introduction as completed with outcome.

        Args:
            intro_id: Introduction ID
            user_id: User marking complete (must be involved)
            outcome: Completion outcome
            notes: Optional outcome notes

        Returns:
            Updated introduction object

        Raises:
            IntroductionServiceError: If validation fails or update errors
        """
        logger.info(
            f"Completing introduction {intro_id} with outcome {outcome.value}"
        )

        try:
            # Fetch introduction
            intro = await zerodb_client.get_by_id(self.table_name, str(intro_id))
            if not intro:
                raise IntroductionServiceError("Introduction not found")

            # Verify user is involved
            if str(user_id) not in [
                intro["requester_id"],
                intro["target_id"],
                intro.get("connector_id")
            ]:
                raise IntroductionServiceError("Not authorized to complete this introduction")

            # Check status - must be accepted to complete
            current_status = intro["status"]
            if current_status not in [
                IntroductionStatus.ACCEPTED.value,
                IntroductionStatus.PENDING.value
            ]:
                raise IntroductionServiceError(
                    f"Cannot complete introduction with status {current_status}"
                )

            # Update to completed
            now = datetime.utcnow().isoformat()
            update_data = {
                "status": IntroductionStatus.COMPLETED.value,
                "outcome": outcome.value,
                "outcome_notes": notes,
                "completed_at": now,
                "updated_at": now
            }

            await zerodb_client.update_rows(
                self.table_name,
                filter={"id": str(intro_id)},
                update={"$set": update_data}
            )

            logger.info(f"Completed introduction {intro_id}")

            # Track outcome in RLHF with success scoring
            try:
                success_outcomes = [
                    IntroductionOutcome.MEETING_SCHEDULED,
                    IntroductionOutcome.EMAIL_EXCHANGED
                ]
                value_score = 1.0 if outcome in success_outcomes else 0.3

                await rlhf_service.track_introduction_outcome(
                    intro_id=intro_id,
                    from_user_id=UUID(intro["requester_id"]),
                    to_user_id=UUID(intro["target_id"]),
                    outcome=outcome.value,
                    value_score=value_score
                )
            except Exception as e:
                logger.warning(f"Failed to track RLHF outcome: {e}")

            # Invalidate caches
            await self._invalidate_user_caches(
                UUID(intro["requester_id"]), UUID(intro["target_id"])
            )

            # Get updated introduction
            updated_intro = await zerodb_client.get_by_id(
                self.table_name, str(intro_id)
            )

            return updated_intro

        except IntroductionServiceError:
            raise
        except Exception as e:
            logger.error(f"Error completing introduction: {e}")
            raise IntroductionServiceError(f"Failed to complete: {e}")

    async def get_received_introductions(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get introduction requests received by user.

        Args:
            user_id: User ID
            status: Optional status filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of introductions
        """
        # Try cache first
        cache_key = f"intros_received:{user_id}:{status}:{limit}:{offset}"
        cached = await cache_service.get(cache_key)
        if cached:
            return cached

        # Build filter
        filter_query = {"target_id": str(user_id)}
        if status:
            filter_query["status"] = status

        # Query database
        introductions = await zerodb_client.query_rows(
            self.table_name,
            filter=filter_query,
            limit=limit,
            offset=offset,
            sort={"requested_at": -1}
        )

        # Cache results
        await cache_service.set(cache_key, introductions, ttl=self.CACHE_TTL)

        return introductions

    async def get_sent_introductions(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get introduction requests sent by user.

        Args:
            user_id: User ID
            status: Optional status filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of introductions
        """
        # Try cache first
        cache_key = f"intros_sent:{user_id}:{status}:{limit}:{offset}"
        cached = await cache_service.get(cache_key)
        if cached:
            return cached

        # Build filter
        filter_query = {"requester_id": str(user_id)}
        if status:
            filter_query["status"] = status

        # Query database
        introductions = await zerodb_client.query_rows(
            self.table_name,
            filter=filter_query,
            limit=limit,
            offset=offset,
            sort={"requested_at": -1}
        )

        # Cache results
        await cache_service.set(cache_key, introductions, ttl=self.CACHE_TTL)

        return introductions

    async def check_existing_introduction(
        self,
        user_a_id: UUID,
        user_b_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Check if introduction already exists between two users.

        Args:
            user_a_id: First user ID
            user_b_id: Second user ID

        Returns:
            Existing introduction or None
        """
        # Check both directions (either could be requester)
        existing = await zerodb_client.query_rows(
            self.table_name,
            filter={
                "$or": [
                    {
                        "requester_id": str(user_a_id),
                        "target_id": str(user_b_id)
                    },
                    {
                        "requester_id": str(user_b_id),
                        "target_id": str(user_a_id)
                    }
                ]
            },
            limit=1
        )

        return existing[0] if existing else None

    async def expire_old_introductions(self) -> int:
        """
        Background job to expire old pending introductions.

        Returns:
            Count of expired introductions
        """
        logger.info("Running introduction expiration job")

        try:
            now = datetime.utcnow().isoformat()

            # Find pending introductions past expiry date
            expired = await zerodb_client.query_rows(
                self.table_name,
                filter={
                    "status": IntroductionStatus.PENDING.value,
                    "expires_at": {"$lt": now}
                }
            )

            count = 0
            for intro in expired:
                try:
                    await self._expire_introduction(UUID(intro["id"]))
                    count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to expire introduction {intro['id']}: {e}"
                    )

            logger.info(f"Expired {count} introductions")
            return count

        except Exception as e:
            logger.error(f"Error in expiration job: {e}")
            return 0

    async def _expire_introduction(self, intro_id: UUID) -> None:
        """
        Mark an introduction as expired.

        Args:
            intro_id: Introduction ID
        """
        now = datetime.utcnow().isoformat()

        await zerodb_client.update_rows(
            self.table_name,
            filter={"id": str(intro_id)},
            update={"$set": {
                "status": IntroductionStatus.EXPIRED.value,
                "updated_at": now
            }}
        )

        logger.info(f"Expired introduction {intro_id}")

    async def _invalidate_user_caches(
        self,
        user_a_id: UUID,
        user_b_id: UUID
    ) -> None:
        """
        Invalidate cached introduction lists for users.

        Args:
            user_a_id: First user ID
            user_b_id: Second user ID
        """
        try:
            # Invalidate all relevant cache keys
            patterns = [
                f"intros_received:{user_a_id}:*",
                f"intros_received:{user_b_id}:*",
                f"intros_sent:{user_a_id}:*",
                f"intros_sent:{user_b_id}:*"
            ]

            for pattern in patterns:
                await cache_service.delete_pattern(pattern)

        except Exception as e:
            logger.warning(f"Failed to invalidate caches: {e}")


# Singleton instance
introduction_service = IntroductionService()
