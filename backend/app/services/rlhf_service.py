"""
RLHF Service - Track user interactions for learning and improving matching quality.

This service uses ZeroDB's RLHF system to:
1. Track goal matching interactions
2. Track discovery feed interactions
3. Track introduction outcomes
4. Learn from user feedback to improve matching algorithms

Architecture:
- Initial feedback is neutral (0.0)
- Feedback updated when outcomes known (e.g., intro accepted = 1.0)
- Agent-level feedback tracks overall performance
- Session-based tracking for complete user journeys
"""
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class RLHFServiceError(Exception):
    """Base exception for RLHF service errors."""
    pass


class RLHFService:
    """
    Manages RLHF (Reinforcement Learning from Human Feedback) tracking.

    Uses ZeroDB RLHF APIs to collect interaction data for improving:
    - Goal matching quality
    - Ask matching accuracy
    - Discovery feed relevance
    - Introduction success rates
    """

    def __init__(self):
        """Initialize RLHF service with ZeroDB configuration."""
        self.project_id = settings.ZERODB_PROJECT_ID
        self.api_key = settings.ZERODB_API_KEY
        self.base_url = f"https://api.ainative.studio/v1/public/{self.project_id}"

        # Agent identifiers for different matching contexts
        self.GOAL_MATCHER_AGENT = "goal_matcher"
        self.ASK_MATCHER_AGENT = "ask_matcher"
        self.DISCOVERY_AGENT = "discovery_feed"
        self.INTRO_AGENT = "smart_introductions"

    async def track_goal_match(
        self,
        query_goal_id: UUID,
        query_goal_description: str,
        matched_goal_ids: List[UUID],
        similarity_scores: List[float],
        context: Dict[str, Any]
    ) -> str:
        """
        Track goal matching interaction for learning.

        Args:
            query_goal_id: ID of the query goal
            query_goal_description: Description of the goal being matched
            matched_goal_ids: List of matched goal IDs
            similarity_scores: Similarity scores for each match
            context: Additional context (user_id, goal_type, etc.)

        Returns:
            Interaction ID from ZeroDB

        Raises:
            RLHFServiceError: If tracking fails
        """
        try:
            # Prepare prompt (what user asked for)
            prompt = f"Find goals similar to: {query_goal_description}"

            # Prepare response (what we returned)
            response_parts = []
            for goal_id, score in zip(matched_goal_ids, similarity_scores):
                response_parts.append(f"Goal {goal_id} (similarity: {score:.2f})")

            response = "\n".join(response_parts) if response_parts else "No matches found"

            # Track interaction with neutral feedback (will be updated later)
            async with httpx.AsyncClient() as client:
                payload = {
                    "agent_id": self.GOAL_MATCHER_AGENT,
                    "prompt": prompt,
                    "response": response,
                    "feedback": 0.0,  # Neutral initially
                    "context": {
                        "query_goal_id": str(query_goal_id),
                        "matched_count": len(matched_goal_ids),
                        "top_score": max(similarity_scores) if similarity_scores else 0.0,
                        "timestamp": datetime.utcnow().isoformat(),
                        **context
                    }
                }

                api_response = await client.post(
                    f"{self.base_url}/rlhf/interaction",
                    headers={
                        "X-Project-ID": self.project_id,
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
                api_response.raise_for_status()
                result = api_response.json()

                interaction_id = result.get("interaction_id")
                logger.info(f"Tracked goal matching interaction: {interaction_id}")
                return interaction_id

        except httpx.HTTPError as e:
            # RLHF tracking is optional - log error but don't crash
            logger.warning(f"RLHF tracking unavailable (goal match): {e}")
            return f"mock-{uuid4()}"  # Return mock ID
        except Exception as e:
            logger.warning(f"RLHF tracking error (goal match): {e}")
            return f"mock-{uuid4()}"  # Return mock ID

    async def track_ask_match(
        self,
        query_ask_id: UUID,
        query_ask_description: str,
        matched_ask_ids: List[UUID],
        similarity_scores: List[float],
        context: Dict[str, Any]
    ) -> str:
        """
        Track ask matching interaction for learning.

        Args:
            query_ask_id: ID of the query ask
            query_ask_description: Description of the ask being matched
            matched_ask_ids: List of matched ask IDs
            similarity_scores: Similarity scores for each match
            context: Additional context (user_id, urgency, etc.)

        Returns:
            Interaction ID from ZeroDB
        """
        try:
            prompt = f"Find asks similar to: {query_ask_description}"

            response_parts = []
            for ask_id, score in zip(matched_ask_ids, similarity_scores):
                response_parts.append(f"Ask {ask_id} (similarity: {score:.2f})")

            response = "\n".join(response_parts) if response_parts else "No matches found"

            async with httpx.AsyncClient() as client:
                payload = {
                    "agent_id": self.ASK_MATCHER_AGENT,
                    "prompt": prompt,
                    "response": response,
                    "feedback": 0.0,
                    "context": {
                        "query_ask_id": str(query_ask_id),
                        "matched_count": len(matched_ask_ids),
                        "top_score": max(similarity_scores) if similarity_scores else 0.0,
                        "timestamp": datetime.utcnow().isoformat(),
                        **context
                    }
                }

                api_response = await client.post(
                    f"{self.base_url}/rlhf/interaction",
                    headers={
                        "X-Project-ID": self.project_id,
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
                api_response.raise_for_status()
                result = api_response.json()

                interaction_id = result.get("interaction_id")
                logger.info(f"Tracked ask matching interaction: {interaction_id}")
                return interaction_id

        except httpx.HTTPError as e:
            logger.warning(f"RLHF tracking unavailable (ask match): {e}")
            return f"mock-{uuid4()}"
        except Exception as e:
            logger.warning(f"RLHF tracking error (ask match): {e}")
            return f"mock-{uuid4()}"

    async def track_discovery_interaction(
        self,
        user_id: UUID,
        user_goals: List[str],
        shown_posts: List[UUID],
        clicked_post_id: Optional[UUID] = None
    ) -> str:
        """
        Track discovery feed interaction.

        Args:
            user_id: User viewing the discovery feed
            user_goals: User's active goals used for discovery
            shown_posts: List of post IDs shown to user
            clicked_post_id: Optional post ID that user clicked

        Returns:
            Interaction ID from ZeroDB
        """
        try:
            prompt = f"Show relevant posts for goals: {', '.join(user_goals[:3])}"
            response = f"Shown {len(shown_posts)} posts"

            # Calculate feedback based on click
            # Clicked = positive feedback, no click = neutral
            feedback = 0.5 if clicked_post_id else 0.0

            async with httpx.AsyncClient() as client:
                payload = {
                    "agent_id": self.DISCOVERY_AGENT,
                    "prompt": prompt,
                    "response": response,
                    "feedback": feedback,
                    "context": {
                        "user_id": str(user_id),
                        "shown_posts": [str(post_id) for post_id in shown_posts],
                        "clicked_post": str(clicked_post_id) if clicked_post_id else None,
                        "goal_count": len(user_goals),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }

                api_response = await client.post(
                    f"{self.base_url}/rlhf/interaction",
                    headers={
                        "X-Project-ID": self.project_id,
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
                api_response.raise_for_status()
                result = api_response.json()

                interaction_id = result.get("interaction_id")
                logger.info(
                    f"Tracked discovery interaction: {interaction_id}, "
                    f"clicked: {clicked_post_id is not None}"
                )
                return interaction_id

        except httpx.HTTPError as e:
            logger.warning(f"RLHF tracking unavailable (discovery): {e}")
            return f"mock-{uuid4()}"
        except Exception as e:
            logger.warning(f"RLHF tracking error (discovery): {e}")
            return f"mock-{uuid4()}"

    async def track_introduction_outcome(
        self,
        intro_id: UUID,
        from_user_id: UUID,
        to_user_id: UUID,
        outcome: str,
        value_score: float
    ) -> str:
        """
        Track introduction outcome for learning.

        Args:
            intro_id: Introduction ID
            from_user_id: User who initiated intro
            to_user_id: User who received intro
            outcome: Outcome status (accepted, declined, ignored)
            value_score: Feedback value (1.0 = accepted, -0.5 = declined, 0.0 = ignored)

        Returns:
            Interaction ID from ZeroDB
        """
        try:
            prompt = f"Suggest introduction between {from_user_id} and {to_user_id}"
            response = f"Introduction suggested"

            async with httpx.AsyncClient() as client:
                payload = {
                    "agent_id": self.INTRO_AGENT,
                    "prompt": prompt,
                    "response": response,
                    "feedback": value_score,
                    "context": {
                        "intro_id": str(intro_id),
                        "from_user_id": str(from_user_id),
                        "to_user_id": str(to_user_id),
                        "outcome": outcome,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }

                api_response = await client.post(
                    f"{self.base_url}/rlhf/interaction",
                    headers={
                        "X-Project-ID": self.project_id,
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
                api_response.raise_for_status()
                result = api_response.json()

                interaction_id = result.get("interaction_id")
                logger.info(
                    f"Tracked introduction outcome: {interaction_id}, "
                    f"outcome: {outcome}, score: {value_score}"
                )
                return interaction_id

        except httpx.HTTPError as e:
            logger.warning(f"RLHF tracking unavailable (intro outcome): {e}")
            return f"mock-{uuid4()}"
        except Exception as e:
            logger.warning(f"RLHF tracking error (intro outcome): {e}")
            return f"mock-{uuid4()}"

    async def provide_agent_feedback(
        self,
        agent_id: str,
        feedback_type: str,
        rating: Optional[float] = None,
        comment: Optional[str] = None
    ) -> str:
        """
        Provide agent-level feedback.

        Args:
            agent_id: Agent identifier (goal_matcher, discovery_feed, etc.)
            feedback_type: Type of feedback (thumbs_up, thumbs_down, rating)
            rating: Optional rating value (1-5 for rating type)
            comment: Optional feedback comment

        Returns:
            Feedback ID from ZeroDB
        """
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "agent_id": agent_id,
                    "feedback_type": feedback_type,
                    "context": {
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }

                if rating is not None:
                    payload["rating"] = rating

                if comment:
                    payload["comment"] = comment

                api_response = await client.post(
                    f"{self.base_url}/rlhf/agent-feedback",
                    headers={
                        "X-Project-ID": self.project_id,
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
                api_response.raise_for_status()
                result = api_response.json()

                feedback_id = result.get("feedback_id")
                logger.info(f"Provided agent feedback: {feedback_id}")
                return feedback_id

        except httpx.HTTPError as e:
            logger.warning(f"RLHF tracking unavailable (feedback): {e}")
            return f"mock-{uuid4()}"
        except Exception as e:
            logger.warning(f"RLHF tracking error (feedback): {e}")
            return f"mock-{uuid4()}"

    async def get_rlhf_insights(self, time_range: str = "day") -> Dict[str, Any]:
        """
        Get RLHF insights and summary statistics.

        Args:
            time_range: Time range for insights (hour, day, week, month)

        Returns:
            Dictionary with RLHF insights
        """
        try:
            async with httpx.AsyncClient() as client:
                params = {"time_range": time_range}

                api_response = await client.get(
                    f"{self.base_url}/rlhf/summary",
                    headers={
                        "X-Project-ID": self.project_id,
                        "X-API-Key": self.api_key
                    },
                    params=params,
                    timeout=30.0
                )
                api_response.raise_for_status()
                insights = api_response.json()

                logger.info(f"Retrieved RLHF insights for time_range: {time_range}")
                return insights

        except httpx.HTTPError as e:
            logger.error(f"Failed to get RLHF insights: {e}")
            # Return empty insights on error (non-critical)
            return {
                "error": str(e),
                "total_interactions": 0,
                "agents": []
            }
        except Exception as e:
            logger.error(f"Unexpected error getting RLHF insights: {e}")
            return {
                "error": str(e),
                "total_interactions": 0,
                "agents": []
            }

    async def track_error(
        self,
        error_type: str,
        error_message: str,
        severity: str = "medium",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Track error for RLHF improvement.

        Args:
            error_type: Error type/category
            error_message: Error message
            severity: Error severity (low, medium, high, critical)
            context: Optional error context

        Returns:
            Error tracking ID
        """
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "error_type": error_type,
                    "error_message": error_message,
                    "severity": severity,
                    "context": context or {}
                }

                api_response = await client.post(
                    f"{self.base_url}/rlhf/error",
                    headers={
                        "X-Project-ID": self.project_id,
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
                api_response.raise_for_status()
                result = api_response.json()

                error_id = result.get("error_id")
                logger.info(f"Tracked error: {error_id}")
                return error_id

        except Exception as e:
            # Don't raise on error tracking failure
            logger.error(f"Failed to track error: {e}")
            return ""

    # ========================================================================
    # Epic 8: Enhanced RLHF Methods for Introduction Outcomes & Learning
    # ========================================================================

    async def track_introduction_with_context(
        self,
        intro_id: UUID,
        requester_id: UUID,
        target_id: UUID,
        match_scores: Dict[str, float],
        matching_context: Dict[str, Any],
        stage: str = "requested",
        outcome_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Track introduction with full matching context for comprehensive RLHF learning.

        This is the primary method for Epic 8 outcome tracking. It captures:
        - Match scores (relevance, trust, reciprocity)
        - Matching signals (goal/ask matches, similarity scores)
        - User context (goal types, industries, location)
        - Outcome data (response, completion, ratings)

        Args:
            intro_id: Introduction ID
            requester_id: User requesting introduction
            target_id: User receiving introduction
            match_scores: Dict with relevance_score, trust_score, reciprocity_score, overall_score
            matching_context: Dict with matching signals, goal types, industry match, etc.
            stage: Lifecycle stage (requested, accepted, declined, completed, expired)
            outcome_data: Optional outcome details (rating, outcome_type, tags, notes)

        Returns:
            RLHF interaction ID

        Example:
            await rlhf_service.track_introduction_with_context(
                intro_id=intro_id,
                requester_id=requester_id,
                target_id=target_id,
                match_scores={
                    "relevance": 0.85,
                    "trust": 0.72,
                    "reciprocity": 0.80,
                    "overall": 0.81
                },
                matching_context={
                    "goal_matches": ["goal_1", "goal_2"],
                    "top_similarity": 0.89,
                    "match_type": "goal_based",
                    "goal_types": ["fundraising"],
                    "industry_match": True
                },
                stage="completed",
                outcome_data={
                    "outcome_type": "meeting_scheduled",
                    "rating": 5,
                    "tags": ["helpful", "valuable"],
                    "time_to_response_hours": 12.5,
                    "time_to_completion_days": 3.2
                }
            )
        """
        try:
            # Build prompt summarizing the match
            prompt = self._build_introduction_prompt(
                requester_id, target_id, match_scores, matching_context
            )

            # Build response summarizing the suggestion
            response = self._build_introduction_response(match_scores, matching_context)

            # Calculate feedback score based on stage and outcome
            feedback_score = self._calculate_feedback_score(stage, outcome_data)

            # Build comprehensive context for learning
            full_context = {
                "intro_id": str(intro_id),
                "requester_id": str(requester_id),
                "target_id": str(target_id),
                "stage": stage,
                "timestamp": datetime.utcnow().isoformat(),

                # Match scores
                "match_scores": match_scores,

                # Matching context
                "matching_context": matching_context,

                # Outcome data (if available)
                **(outcome_data or {})
            }

            # Track with ZeroDB RLHF
            async with httpx.AsyncClient() as client:
                payload = {
                    "agent_id": self.INTRO_AGENT,
                    "prompt": prompt,
                    "response": response,
                    "feedback": feedback_score,
                    "context": full_context
                }

                api_response = await client.post(
                    f"{self.base_url}/rlhf/interaction",
                    headers={
                        "X-Project-ID": self.project_id,
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
                api_response.raise_for_status()
                result = api_response.json()

                interaction_id = result.get("interaction_id")
                logger.info(
                    f"Tracked introduction {intro_id} at stage {stage}: "
                    f"feedback={feedback_score:.2f}, interaction_id={interaction_id}"
                )
                return interaction_id

        except Exception as e:
            logger.warning(f"RLHF tracking error (intro context): {e}")
            return f"mock-{uuid4()}"

    def _build_introduction_prompt(
        self,
        requester_id: UUID,
        target_id: UUID,
        match_scores: Dict[str, float],
        matching_context: Dict[str, Any]
    ) -> str:
        """Build human-readable prompt describing the matching request."""

        goal_types = matching_context.get("goal_types", [])
        match_type = matching_context.get("match_type", "unknown")
        industry_match = matching_context.get("industry_match", False)

        prompt_parts = [
            f"Suggest introduction between {requester_id} and {target_id}",
            f"Goal types: {', '.join(goal_types) if goal_types else 'unknown'}",
            f"Match type: {match_type}",
            f"Industry match: {'yes' if industry_match else 'no'}"
        ]

        return " | ".join(prompt_parts)

    def _build_introduction_response(
        self,
        match_scores: Dict[str, float],
        matching_context: Dict[str, Any]
    ) -> str:
        """Build human-readable response describing the match quality."""

        overall = match_scores.get("overall", 0.0)
        relevance = match_scores.get("relevance", 0.0)
        trust = match_scores.get("trust", 0.0)
        reciprocity = match_scores.get("reciprocity", 0.0)

        top_similarity = matching_context.get("top_similarity", 0.0)
        num_matches = (
            len(matching_context.get("goal_matches", [])) +
            len(matching_context.get("ask_matches", []))
        )

        response = (
            f"Match score: {overall:.2f} "
            f"(relevance: {relevance:.2f}, trust: {trust:.2f}, reciprocity: {reciprocity:.2f}) | "
            f"Similarity: {top_similarity:.2f} | "
            f"Signals: {num_matches} matches"
        )

        return response

    def _calculate_feedback_score(
        self,
        stage: str,
        outcome_data: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate RLHF feedback score based on introduction stage and outcome.

        Scoring rubric (based on RLHF_STRATEGY.md):
        - requested: 0.0 (neutral, no outcome yet)
        - accepted: 0.5 (positive signal, but not complete)
        - declined: -0.3 (negative but not catastrophic)
        - expired: -0.1 (neutral negative, may be timing)
        - completed: 0.0-1.0 based on outcome quality

        For completed stage, composite score from:
        - Rating (if available): 1-5 stars → 0.0-1.0
        - Outcome type: meeting_scheduled=1.0, email_exchanged=0.8, no_response=0.2, not_relevant=0.0
        - Response speed: faster = higher score
        - Tags: positive tags boost, negative tags reduce
        """
        if stage == "requested":
            return 0.0

        elif stage == "accepted":
            return 0.5

        elif stage == "declined":
            return -0.3

        elif stage == "expired":
            return -0.1

        elif stage == "completed" and outcome_data:
            return self._calculate_completion_score(outcome_data)

        else:
            return 0.0

    def _calculate_completion_score(self, outcome_data: Dict[str, Any]) -> float:
        """
        Calculate composite score for completed introductions.

        Implements the formula from RLHF_STRATEGY.md:
        - 60% explicit feedback (rating + outcome type)
        - 25% behavioral signals (response time, completion time)
        - 15% contextual signals (tags, notes sentiment)
        """
        # Explicit feedback (60%)
        rating = outcome_data.get("rating")
        outcome_type = outcome_data.get("outcome_type")

        rating_score = 0.5  # Default if no rating
        if rating:
            rating_score = (rating - 1) / 4  # Normalize 1-5 to 0-1

        outcome_weights = {
            "meeting_scheduled": 1.0,
            "email_exchanged": 0.8,
            "no_response": 0.2,
            "not_relevant": 0.0
        }
        outcome_score = outcome_weights.get(outcome_type, 0.5)

        explicit_score = (rating_score * 0.5 + outcome_score * 0.5) * 0.6

        # Behavioral signals (25%)
        response_speed = self._calculate_response_speed_score(
            outcome_data.get("time_to_response_hours", 48)
        )
        completion_speed = self._calculate_completion_speed_score(
            outcome_data.get("time_to_completion_days", 7)
        )

        behavioral_score = (response_speed * 0.6 + completion_speed * 0.4) * 0.25

        # Contextual signals (15%)
        tags = outcome_data.get("tags", [])
        tag_score = self._calculate_tag_sentiment_score(tags)

        contextual_score = tag_score * 0.15

        # Composite score
        final_score = explicit_score + behavioral_score + contextual_score

        return min(1.0, max(0.0, final_score))

    def _calculate_response_speed_score(self, hours: float) -> float:
        """Score based on response speed (faster = better)."""
        if hours < 12:
            return 1.0
        elif hours < 24:
            return 0.8
        elif hours < 48:
            return 0.6
        elif hours < 72:
            return 0.4
        else:
            return 0.2

    def _calculate_completion_speed_score(self, days: float) -> float:
        """Score based on completion speed (faster = better)."""
        if days < 3:
            return 1.0
        elif days < 5:
            return 0.8
        elif days < 7:
            return 0.6
        elif days < 14:
            return 0.4
        else:
            return 0.2

    def _calculate_tag_sentiment_score(self, tags: List[str]) -> float:
        """Score based on outcome tags."""
        positive_tags = {"helpful", "valuable", "great-match", "timely", "relevant"}
        negative_tags = {"not-relevant", "bad-match", "spam", "timing-off", "too-busy"}

        positive_count = sum(1 for tag in tags if tag in positive_tags)
        negative_count = sum(1 for tag in tags if tag in negative_tags)

        if not tags:
            return 0.5

        # Net sentiment
        net = positive_count - negative_count
        normalized = (net + len(tags)) / (2 * len(tags))  # Normalize to 0-1

        return max(0.0, min(1.0, normalized))

    async def get_matching_quality_metrics(
        self,
        time_range: str = "week",
        group_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get overall matching quality metrics from RLHF data.

        Args:
            time_range: Time range (day, week, month)
            group_by: Optional grouping (goal_type, match_type, score_range)

        Returns:
            Dict with comprehensive metrics
        """
        try:
            # Get RLHF summary for introduction agent
            async with httpx.AsyncClient() as client:
                params = {
                    "agent_id": self.INTRO_AGENT,
                    "time_range": time_range
                }

                api_response = await client.get(
                    f"{self.base_url}/rlhf/summary",
                    headers={
                        "X-Project-ID": self.project_id,
                        "X-API-Key": self.api_key
                    },
                    params=params,
                    timeout=30.0
                )
                api_response.raise_for_status()
                summary = api_response.json()

                # Extract key metrics
                metrics = {
                    "total_introductions": summary.get("total_interactions", 0),
                    "avg_feedback_score": summary.get("avg_feedback", 0.0),
                    "feedback_distribution": summary.get("feedback_distribution", {}),

                    # Calculate derived metrics
                    "success_rate": self._calculate_success_rate(summary),
                    "response_rate": self._calculate_response_rate(summary),
                    "completion_rate": self._calculate_completion_rate(summary),

                    # Time range
                    "time_range": time_range,
                    "retrieved_at": datetime.utcnow().isoformat()
                }

                return metrics

        except Exception as e:
            logger.error(f"Failed to get matching quality metrics: {e}")
            return {
                "error": str(e),
                "total_introductions": 0,
                "avg_feedback_score": 0.0
            }

    def _calculate_success_rate(self, summary: Dict) -> float:
        """Calculate success rate from RLHF summary."""
        # Success = feedback > 0.6
        feedback_dist = summary.get("feedback_distribution", {})
        total = sum(feedback_dist.values())

        if total == 0:
            return 0.0

        success_count = sum(
            count for score, count in feedback_dist.items()
            if float(score) > 0.6
        )

        return success_count / total

    def _calculate_response_rate(self, summary: Dict) -> float:
        """Calculate response rate (accepted / total)."""
        # This would need additional tracking in context
        # For now, estimate from feedback scores > 0
        feedback_dist = summary.get("feedback_distribution", {})
        total = sum(feedback_dist.values())

        if total == 0:
            return 0.0

        responded = sum(
            count for score, count in feedback_dist.items()
            if float(score) != 0.0  # Any non-neutral feedback
        )

        return responded / total

    def _calculate_completion_rate(self, summary: Dict) -> float:
        """Calculate completion rate (completed / accepted)."""
        # Estimate from high feedback scores
        feedback_dist = summary.get("feedback_distribution", {})
        total_responded = sum(
            count for score, count in feedback_dist.items()
            if float(score) > 0.0
        )

        if total_responded == 0:
            return 0.0

        completed = sum(
            count for score, count in feedback_dist.items()
            if float(score) > 0.5  # Completed threshold
        )

        return completed / total_responded

    async def get_factor_importance(
        self,
        time_range: str = "month"
    ) -> Dict[str, Any]:
        """
        Analyze which match factors (relevance, trust, reciprocity) predict success.

        This would ideally query historical data and run correlation analysis.
        For now, returns a structure for factor importance analysis.

        Returns:
            Dict with factor correlations and importance scores
        """
        # This is a placeholder for future ML analysis
        # Would need to:
        # 1. Query all RLHF interactions with context
        # 2. Extract match_scores and feedback_scores
        # 3. Calculate correlation between each factor and success
        # 4. Determine optimal weights

        return {
            "analysis_type": "factor_importance",
            "time_range": time_range,
            "note": "Requires historical data analysis - see ML_TRAINING_PLAN.md",

            # Placeholder structure
            "correlations": {
                "relevance_score": 0.78,  # Example: high correlation
                "trust_score": 0.52,      # Example: moderate correlation
                "reciprocity_score": 0.61 # Example: moderate-high correlation
            },

            "recommended_weights": {
                "relevance": 0.55,    # Current: 0.50
                "trust": 0.25,        # Current: 0.25
                "reciprocity": 0.20   # Current: 0.25
            },

            "confidence": "low",  # Would increase with more data
            "sample_size": 0
        }

    async def get_training_dataset(
        self,
        limit: int = 1000,
        min_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Export RLHF data as training dataset for ML models.

        Args:
            limit: Maximum number of records to export
            min_date: Optional ISO date string for filtering

        Returns:
            List of training examples with features and labels
        """
        try:
            # Query RLHF interactions for introduction agent
            async with httpx.AsyncClient() as client:
                params = {
                    "agent_id": self.INTRO_AGENT,
                    "limit": limit
                }

                if min_date:
                    params["since"] = min_date

                api_response = await client.get(
                    f"{self.base_url}/rlhf/interactions",
                    headers={
                        "X-Project-ID": self.project_id,
                        "X-API-Key": self.api_key
                    },
                    params=params,
                    timeout=60.0
                )
                api_response.raise_for_status()
                interactions = api_response.json()

                # Transform to training format
                training_data = []
                for interaction in interactions.get("interactions", []):
                    context = interaction.get("context", {})

                    # Extract features
                    training_example = {
                        # Match scores (features)
                        "relevance_score": context.get("match_scores", {}).get("relevance", 0.5),
                        "trust_score": context.get("match_scores", {}).get("trust", 0.5),
                        "reciprocity_score": context.get("match_scores", {}).get("reciprocity", 0.5),
                        "overall_score": context.get("match_scores", {}).get("overall", 0.5),

                        # Matching context (features)
                        "num_goal_matches": len(context.get("matching_context", {}).get("goal_matches", [])),
                        "num_ask_matches": len(context.get("matching_context", {}).get("ask_matches", [])),
                        "top_similarity": context.get("matching_context", {}).get("top_similarity", 0.0),
                        "match_type": context.get("matching_context", {}).get("match_type", "unknown"),
                        "industry_match": context.get("matching_context", {}).get("industry_match", False),

                        # Target variable (label)
                        "feedback_score": interaction.get("feedback", 0.0),
                        "success": interaction.get("feedback", 0.0) > 0.6,

                        # Metadata
                        "intro_id": context.get("intro_id"),
                        "stage": context.get("stage"),
                        "timestamp": interaction.get("timestamp")
                    }

                    training_data.append(training_example)

                logger.info(f"Exported {len(training_data)} training examples")
                return training_data

        except Exception as e:
            logger.error(f"Failed to export training dataset: {e}")
            return []

    async def calculate_success_rate(
        self,
        user_id: UUID,
        as_requester: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate introduction success rate for a specific user.

        Args:
            user_id: User to calculate metrics for
            as_requester: If True, analyze as requester; if False, as target

        Returns:
            Dict with user-specific success metrics
        """
        try:
            # Query RLHF interactions for this user
            async with httpx.AsyncClient() as client:
                params = {
                    "agent_id": self.INTRO_AGENT
                }

                api_response = await client.get(
                    f"{self.base_url}/rlhf/interactions",
                    headers={
                        "X-Project-ID": self.project_id,
                        "X-API-Key": self.api_key
                    },
                    params=params,
                    timeout=30.0
                )
                api_response.raise_for_status()
                all_interactions = api_response.json()

                # Filter for this user
                user_id_str = str(user_id)
                field = "requester_id" if as_requester else "target_id"

                user_interactions = [
                    i for i in all_interactions.get("interactions", [])
                    if i.get("context", {}).get(field) == user_id_str
                ]

                # Calculate metrics
                total = len(user_interactions)
                if total == 0:
                    return {
                        "user_id": user_id_str,
                        "role": "requester" if as_requester else "target",
                        "total_introductions": 0,
                        "success_rate": 0.0,
                        "avg_feedback_score": 0.0
                    }

                feedback_scores = [i.get("feedback", 0.0) for i in user_interactions]
                successes = sum(1 for score in feedback_scores if score > 0.6)

                return {
                    "user_id": user_id_str,
                    "role": "requester" if as_requester else "target",
                    "total_introductions": total,
                    "success_rate": successes / total,
                    "avg_feedback_score": sum(feedback_scores) / total,
                    "success_count": successes
                }

        except Exception as e:
            logger.error(f"Failed to calculate user success rate: {e}")
            return {
                "user_id": str(user_id),
                "error": str(e),
                "total_introductions": 0,
                "success_rate": 0.0
            }


# Singleton instance
rlhf_service = RLHFService()
