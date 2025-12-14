"""
Outcome Service - Manages introduction outcome tracking and analytics.

This service handles:
1. Recording introduction outcomes
2. Updating existing outcomes
3. Retrieving outcome data
4. Generating outcome analytics
5. RLHF integration for learning

Architecture:
- ZeroDB for NoSQL storage in 'introduction_outcomes' table
- RLHF service for outcome tracking and learning
- Cache service for performance optimization
- Permission validation (only participants can record outcomes)

Story 8.1: Record Intro Outcome
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from collections import Counter

from app.services.zerodb_client import zerodb_client
from app.services.rlhf_service import rlhf_service
from app.services.cache_service import cache_service
from app.schemas.outcome import OutcomeType

logger = logging.getLogger(__name__)


class OutcomeServiceError(Exception):
    """Base exception for outcome service errors."""
    pass


class OutcomeService:
    """
    Manages introduction outcome lifecycle and analytics.

    Key Features:
    - Outcome recording with validation
    - Permission checks (only participants)
    - RLHF tracking for learning
    - Analytics generation
    - Cache management
    """

    CACHE_TTL = 300  # 5 minutes

    def __init__(self):
        """Initialize outcome service."""
        self.table_name = "introduction_outcomes"
        self.intro_table_name = "introductions"

    async def record_outcome(
        self,
        intro_id: UUID,
        user_id: UUID,
        outcome_type: OutcomeType,
        feedback_text: Optional[str] = None,
        rating: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Record an introduction outcome.

        Args:
            intro_id: Introduction ID
            user_id: User recording the outcome (must be participant)
            outcome_type: Type of outcome
            feedback_text: Optional detailed feedback (10-500 chars)
            rating: Optional rating 1-5
            tags: Optional tags for categorization

        Returns:
            Created outcome object

        Raises:
            OutcomeServiceError: If validation fails or creation errors
        """
        logger.info(
            f"Recording outcome for introduction {intro_id} by user {user_id}: "
            f"{outcome_type.value}"
        )

        try:
            # Validate introduction exists
            introduction = await zerodb_client.get_by_id(
                self.intro_table_name, str(intro_id)
            )
            if not introduction:
                raise OutcomeServiceError("Introduction not found")

            # Verify user is a participant (requester or target)
            if str(user_id) not in [
                introduction["requester_id"],
                introduction["target_id"]
            ]:
                raise OutcomeServiceError(
                    "Only introduction participants can record outcomes"
                )

            # Check if outcome already exists for this introduction
            existing_outcomes = await zerodb_client.query_rows(
                self.table_name,
                filter={"introduction_id": str(intro_id)},
                limit=1
            )

            if existing_outcomes:
                raise OutcomeServiceError(
                    "Outcome already exists for this introduction. Use update instead."
                )

            # Generate unique ID
            outcome_id = str(uuid4())
            now = datetime.utcnow().isoformat()

            # Prepare outcome data
            outcome_data = {
                "id": outcome_id,
                "introduction_id": str(intro_id),
                "user_id": str(user_id),
                "outcome_type": outcome_type.value,
                "feedback_text": feedback_text,
                "rating": rating,
                "tags": tags or [],
                "created_at": now,
                "updated_at": now
            }

            # Insert into database
            await zerodb_client.insert_rows(self.table_name, [outcome_data])

            logger.info(f"Created outcome {outcome_id} for introduction {intro_id}")

            # Track in RLHF for learning
            try:
                await self._track_rlhf(
                    intro_id=intro_id,
                    introduction=introduction,
                    outcome_type=outcome_type,
                    rating=rating,
                    feedback_text=feedback_text
                )
            except Exception as e:
                logger.warning(f"Failed to track RLHF: {e}")

            # Invalidate relevant caches
            await self._invalidate_caches(intro_id, user_id)

            return outcome_data

        except OutcomeServiceError:
            raise
        except Exception as e:
            logger.error(f"Error recording outcome: {e}")
            raise OutcomeServiceError(f"Failed to record outcome: {e}")

    async def get_outcome(self, intro_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get outcome for an introduction.

        Args:
            intro_id: Introduction ID

        Returns:
            Outcome object or None if not found
        """
        try:
            # Try cache first
            cache_key = f"outcome:{intro_id}"
            cached = await cache_service.get(cache_key)
            if cached:
                return cached

            # Query database
            outcomes = await zerodb_client.query_rows(
                self.table_name,
                filter={"introduction_id": str(intro_id)},
                limit=1
            )

            if not outcomes:
                return None

            outcome = outcomes[0]

            # Cache result
            await cache_service.set(cache_key, outcome, ttl=self.CACHE_TTL)

            return outcome

        except Exception as e:
            logger.error(f"Error getting outcome for intro {intro_id}: {e}")
            raise OutcomeServiceError(f"Failed to get outcome: {e}")

    async def update_outcome(
        self,
        intro_id: UUID,
        user_id: UUID,
        outcome_type: Optional[OutcomeType] = None,
        feedback_text: Optional[str] = None,
        rating: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing outcome.

        Args:
            intro_id: Introduction ID
            user_id: User updating the outcome (must be original recorder)
            outcome_type: Updated outcome type
            feedback_text: Updated feedback text
            rating: Updated rating
            tags: Updated tags

        Returns:
            Updated outcome object

        Raises:
            OutcomeServiceError: If validation fails or update errors
        """
        logger.info(f"Updating outcome for introduction {intro_id} by user {user_id}")

        try:
            # Validate introduction exists
            introduction = await zerodb_client.get_by_id(
                self.intro_table_name, str(intro_id)
            )
            if not introduction:
                raise OutcomeServiceError("Introduction not found")

            # Verify user is a participant
            if str(user_id) not in [
                introduction["requester_id"],
                introduction["target_id"]
            ]:
                raise OutcomeServiceError(
                    "Only introduction participants can update outcomes"
                )

            # Get existing outcome
            existing_outcome = await self.get_outcome(intro_id)
            if not existing_outcome:
                raise OutcomeServiceError("Outcome not found. Use record instead.")

            # Build update data
            update_data = {"updated_at": datetime.utcnow().isoformat()}

            if outcome_type is not None:
                update_data["outcome_type"] = outcome_type.value
            if feedback_text is not None:
                update_data["feedback_text"] = feedback_text
            if rating is not None:
                update_data["rating"] = rating
            if tags is not None:
                update_data["tags"] = tags

            # Update in database
            await zerodb_client.update_rows(
                self.table_name,
                filter={"introduction_id": str(intro_id)},
                update={"$set": update_data}
            )

            logger.info(f"Updated outcome for introduction {intro_id}")

            # Track updated outcome in RLHF
            try:
                final_outcome_type = (
                    outcome_type if outcome_type
                    else OutcomeType(existing_outcome["outcome_type"])
                )
                final_rating = rating if rating is not None else existing_outcome.get("rating")

                await self._track_rlhf(
                    intro_id=intro_id,
                    introduction=introduction,
                    outcome_type=final_outcome_type,
                    rating=final_rating,
                    feedback_text=feedback_text or existing_outcome.get("feedback_text")
                )
            except Exception as e:
                logger.warning(f"Failed to track RLHF update: {e}")

            # Invalidate caches
            await self._invalidate_caches(intro_id, user_id)

            # Get updated outcome
            updated_outcome = await zerodb_client.query_rows(
                self.table_name,
                filter={"introduction_id": str(intro_id)},
                limit=1
            )

            return updated_outcome[0] if updated_outcome else existing_outcome

        except OutcomeServiceError:
            raise
        except Exception as e:
            logger.error(f"Error updating outcome: {e}")
            raise OutcomeServiceError(f"Failed to update outcome: {e}")

    async def get_outcome_analytics(
        self,
        user_id: UUID,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get outcome analytics for a user.

        Args:
            user_id: User ID
            period_start: Optional start date for analytics period
            period_end: Optional end date for analytics period

        Returns:
            Analytics dictionary with breakdowns and statistics
        """
        logger.info(f"Generating outcome analytics for user {user_id}")

        try:
            # Build filter
            filter_query = {"user_id": str(user_id)}

            if period_start or period_end:
                date_filter = {}
                if period_start:
                    date_filter["$gte"] = period_start.isoformat()
                if period_end:
                    date_filter["$lte"] = period_end.isoformat()
                filter_query["created_at"] = date_filter

            # Query all outcomes for user
            outcomes = await zerodb_client.query_rows(
                self.table_name,
                filter=filter_query,
                limit=1000  # Reasonable limit for analytics
            )

            if not outcomes:
                return self._empty_analytics(user_id, period_start, period_end)

            # Calculate analytics
            total_outcomes = len(outcomes)
            outcome_counts = Counter(o["outcome_type"] for o in outcomes)

            # Calculate ratings
            ratings = [o["rating"] for o in outcomes if o.get("rating") is not None]
            avg_rating = sum(ratings) / len(ratings) if ratings else None

            # Calculate outcome breakdown
            outcome_breakdown = []
            for outcome_type in OutcomeType:
                count = outcome_counts.get(outcome_type.value, 0)
                percentage = (count / total_outcomes * 100) if total_outcomes > 0 else 0.0

                # Calculate average rating for this outcome type
                type_ratings = [
                    o["rating"] for o in outcomes
                    if o["outcome_type"] == outcome_type.value and o.get("rating") is not None
                ]
                type_avg_rating = sum(type_ratings) / len(type_ratings) if type_ratings else None

                outcome_breakdown.append({
                    "outcome_type": outcome_type.value,
                    "count": count,
                    "percentage": round(percentage, 1),
                    "avg_rating": round(type_avg_rating, 1) if type_avg_rating else None
                })

            # Calculate top tags
            all_tags = []
            for outcome in outcomes:
                all_tags.extend(outcome.get("tags", []))

            tag_counts = Counter(all_tags)
            top_tags = [
                {"tag": tag, "count": count}
                for tag, count in tag_counts.most_common(10)
            ]

            # Calculate success metrics
            successful_count = outcome_counts.get(OutcomeType.SUCCESSFUL.value, 0)
            unsuccessful_count = outcome_counts.get(OutcomeType.UNSUCCESSFUL.value, 0)

            success_rate = (
                (successful_count / total_outcomes * 100) if total_outcomes > 0 else 0.0
            )
            response_rate = (
                ((successful_count + unsuccessful_count) / total_outcomes * 100)
                if total_outcomes > 0 else 0.0
            )

            analytics = {
                "user_id": str(user_id),
                "total_outcomes": total_outcomes,
                "outcome_breakdown": outcome_breakdown,
                "average_rating": round(avg_rating, 1) if avg_rating else None,
                "top_tags": top_tags,
                "success_rate": round(success_rate, 1),
                "response_rate": round(response_rate, 1),
                "period_start": period_start.isoformat() if period_start else None,
                "period_end": period_end.isoformat() if period_end else None
            }

            logger.info(
                f"Generated analytics for user {user_id}: "
                f"{total_outcomes} outcomes, {success_rate:.1f}% success rate"
            )

            return analytics

        except Exception as e:
            logger.error(f"Error generating analytics for user {user_id}: {e}")
            raise OutcomeServiceError(f"Failed to generate analytics: {e}")

    async def _track_rlhf(
        self,
        intro_id: UUID,
        introduction: Dict[str, Any],
        outcome_type: OutcomeType,
        rating: Optional[int],
        feedback_text: Optional[str]
    ) -> None:
        """
        Track outcome in RLHF system for learning.

        Args:
            intro_id: Introduction ID
            introduction: Introduction object with context
            outcome_type: Outcome type
            rating: Optional rating
            feedback_text: Optional feedback text
        """
        try:
            # Calculate feedback score based on outcome and rating
            # successful = positive, unsuccessful = neutral, no_response/not_relevant = negative
            base_scores = {
                OutcomeType.SUCCESSFUL: 1.0,
                OutcomeType.UNSUCCESSFUL: 0.3,
                OutcomeType.NO_RESPONSE: -0.3,
                OutcomeType.NOT_RELEVANT: -0.5
            }

            value_score = base_scores.get(outcome_type, 0.0)

            # Adjust score based on rating if provided
            if rating is not None:
                # Rating of 5 = full score, rating of 1 = negative adjustment
                rating_adjustment = (rating - 3) * 0.2  # Scale: -0.4 to +0.4
                value_score = max(-1.0, min(1.0, value_score + rating_adjustment))

            # Build context for RLHF
            context = {
                "intro_id": str(intro_id),
                "outcome_type": outcome_type.value,
                "rating": rating,
                "has_feedback": feedback_text is not None,
                "requester_id": introduction["requester_id"],
                "target_id": introduction["target_id"],
                "intro_status": introduction.get("status"),
                "intro_context": introduction.get("context", {})
            }

            # Track outcome
            await rlhf_service.track_introduction_outcome(
                intro_id=intro_id,
                from_user_id=UUID(introduction["requester_id"]),
                to_user_id=UUID(introduction["target_id"]),
                outcome=outcome_type.value,
                value_score=value_score
            )

            logger.info(
                f"Tracked RLHF for intro {intro_id}: "
                f"{outcome_type.value}, score={value_score:.2f}"
            )

        except Exception as e:
            logger.error(f"Failed to track RLHF: {e}")
            # Don't raise - RLHF tracking is non-critical
            raise

    async def _invalidate_caches(self, intro_id: UUID, user_id: UUID) -> None:
        """
        Invalidate cached outcome and analytics data.

        Args:
            intro_id: Introduction ID
            user_id: User ID
        """
        try:
            cache_keys = [
                f"outcome:{intro_id}",
                f"analytics:{user_id}"
            ]

            for key in cache_keys:
                await cache_service.delete(key)

        except Exception as e:
            logger.warning(f"Failed to invalidate caches: {e}")

    def _empty_analytics(
        self,
        user_id: UUID,
        period_start: Optional[datetime],
        period_end: Optional[datetime]
    ) -> Dict[str, Any]:
        """
        Generate empty analytics response.

        Args:
            user_id: User ID
            period_start: Period start
            period_end: Period end

        Returns:
            Empty analytics dictionary
        """
        outcome_breakdown = [
            {
                "outcome_type": outcome_type.value,
                "count": 0,
                "percentage": 0.0,
                "avg_rating": None
            }
            for outcome_type in OutcomeType
        ]

        return {
            "user_id": str(user_id),
            "total_outcomes": 0,
            "outcome_breakdown": outcome_breakdown,
            "average_rating": None,
            "top_tags": [],
            "success_rate": 0.0,
            "response_rate": 0.0,
            "period_start": period_start.isoformat() if period_start else None,
            "period_end": period_end.isoformat() if period_end else None
        }


# Singleton instance
outcome_service = OutcomeService()
