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
from uuid import UUID
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
        self.base_url = "https://api.zerodb.ai/v1"

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
            logger.error(f"Failed to track goal match: {e}")
            raise RLHFServiceError(f"Failed to track goal match: {e}")
        except Exception as e:
            logger.error(f"Unexpected error tracking goal match: {e}")
            raise RLHFServiceError(f"Unexpected error: {e}")

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
            logger.error(f"Failed to track ask match: {e}")
            raise RLHFServiceError(f"Failed to track ask match: {e}")
        except Exception as e:
            logger.error(f"Unexpected error tracking ask match: {e}")
            raise RLHFServiceError(f"Unexpected error: {e}")

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
            logger.error(f"Failed to track discovery interaction: {e}")
            raise RLHFServiceError(f"Failed to track discovery: {e}")
        except Exception as e:
            logger.error(f"Unexpected error tracking discovery: {e}")
            raise RLHFServiceError(f"Unexpected error: {e}")

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
            logger.error(f"Failed to track introduction outcome: {e}")
            raise RLHFServiceError(f"Failed to track introduction: {e}")
        except Exception as e:
            logger.error(f"Unexpected error tracking introduction: {e}")
            raise RLHFServiceError(f"Unexpected error: {e}")

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
            logger.error(f"Failed to provide agent feedback: {e}")
            raise RLHFServiceError(f"Failed to provide feedback: {e}")
        except Exception as e:
            logger.error(f"Unexpected error providing feedback: {e}")
            raise RLHFServiceError(f"Unexpected error: {e}")

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


# Singleton instance
rlhf_service = RLHFService()
