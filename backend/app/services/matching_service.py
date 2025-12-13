"""
Matching Service - Intelligent introduction suggestion system.

This service implements semantic matching to recommend valuable connections
between founders based on their goals, asks, and profiles.

Matching Algorithm:
1. Stage 1: Retrieve user's active goals and asks
2. Stage 2: Vector search for semantically similar content
3. Stage 3: Calculate detailed match scores (relevance, trust, reciprocity)
4. Stage 4: Generate human-readable reasoning and rank results

Score Components:
- Relevance Score: Semantic similarity of goals/asks (0-1)
- Trust Score: Network quality and user reputation (0-1)
- Reciprocity Score: Mutual value potential (0-1)
- Overall Score: Weighted combination of above scores
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.services.zerodb_client import zerodb_client
from app.services.embedding_service import embedding_service, EmbeddingServiceError
from app.services.safety_service import safety_service

logger = logging.getLogger(__name__)


class MatchingServiceError(Exception):
    """Base exception for matching service errors."""
    pass


class MatchingService:
    """
    Manages intelligent introduction suggestions using semantic matching.

    Key Features:
    - Multi-signal matching (goals + asks)
    - Reciprocal value assessment
    - Network quality scoring
    - Human-readable reasoning generation
    """

    # Scoring weights
    RELEVANCE_WEIGHT = 0.5
    TRUST_WEIGHT = 0.25
    RECIPROCITY_WEIGHT = 0.25

    # Minimum thresholds
    MIN_RELEVANCE_SCORE = 0.5
    MIN_OVERALL_SCORE = 0.6

    # Vector search parameters
    SEARCH_LIMIT_PER_SIGNAL = 50
    SIMILARITY_THRESHOLD = 0.6

    async def suggest_introductions(
        self,
        user_id: UUID,
        limit: int = 20,
        min_score: float = 0.6,
        match_type: str = "all"
    ) -> List[Dict]:
        """
        Generate introduction suggestions for a user.

        Args:
            user_id: User to generate suggestions for
            limit: Maximum number of suggestions to return
            min_score: Minimum overall match score threshold (0-1)
            match_type: Type of matching - "goal_based", "ask_based", or "all"

        Returns:
            List of match dictionaries with scores and reasoning

        Raises:
            MatchingServiceError: If suggestion generation fails
        """
        try:
            logger.info(f"Generating introduction suggestions for user {user_id}")

            # Stage 1: Get user's active goals and asks
            user_goals = await zerodb_client.query_rows(
                table_name="goals",
                filter={"user_id": str(user_id), "is_active": True}
            )

            user_asks = await zerodb_client.query_rows(
                table_name="asks",
                filter={"user_id": str(user_id), "status": "open"}
            )

            if not user_goals and not user_asks:
                logger.warning(f"User {user_id} has no active goals or asks")
                return []

            # Stage 2: Vector search for similar profiles
            candidates = await self._find_candidates(
                user_id=user_id,
                user_goals=user_goals,
                user_asks=user_asks,
                match_type=match_type
            )

            if not candidates:
                logger.info(f"No candidates found for user {user_id}")
                return []

            # Stage 3: Calculate detailed scores for each candidate
            scored_matches = await self._score_candidates(
                user_id=user_id,
                user_goals=user_goals,
                user_asks=user_asks,
                candidates=candidates,
                min_score=min_score
            )

            # Stage 4: Rank and return top N
            scored_matches.sort(key=lambda x: x["match_score"]["overall_score"], reverse=True)
            top_matches = scored_matches[:limit]

            logger.info(
                f"Generated {len(top_matches)} suggestions for user {user_id} "
                f"(from {len(scored_matches)} qualifying matches)"
            )

            return top_matches

        except Exception as e:
            logger.error(f"Error generating suggestions for user {user_id}: {e}")
            raise MatchingServiceError(f"Failed to generate suggestions: {e}")

    async def _find_candidates(
        self,
        user_id: UUID,
        user_goals: List[Dict],
        user_asks: List[Dict],
        match_type: str
    ) -> List[Dict]:
        """
        Find candidate users through vector search.

        Args:
            user_id: User ID to exclude from results
            user_goals: User's active goals
            user_asks: User's open asks
            match_type: Type of matching to perform

        Returns:
            List of candidate dictionaries with metadata
        """
        candidates_map = {}  # Use dict to deduplicate by user_id

        # Search based on goals
        if match_type in ["goal_based", "all"] and user_goals:
            for goal in user_goals:
                if not goal.get("embedding_id"):
                    continue

                try:
                    # Find users with complementary goals or expertise
                    goal_text = f"{goal['type']}: {goal['description']}"
                    results = await embedding_service.search_similar(
                        query_text=goal_text,
                        entity_type="goal",
                        limit=self.SEARCH_LIMIT_PER_SIGNAL,
                        min_similarity=self.SIMILARITY_THRESHOLD
                    )

                    for result in results:
                        result_user_id = result.get("metadata", {}).get("user_id")
                        if not result_user_id or result_user_id == str(user_id):
                            continue

                        if result_user_id not in candidates_map:
                            candidates_map[result_user_id] = {
                                "user_id": result_user_id,
                                "matching_signals": [],
                                "max_similarity": 0.0
                            }

                        # Track matching signal
                        similarity = result.get("similarity", 0.0)
                        candidates_map[result_user_id]["matching_signals"].append({
                            "type": "goal",
                            "source_id": goal["id"],
                            "source_text": goal["description"],
                            "match_id": result.get("metadata", {}).get("source_id"),
                            "similarity": similarity
                        })

                        # Update max similarity
                        if similarity > candidates_map[result_user_id]["max_similarity"]:
                            candidates_map[result_user_id]["max_similarity"] = similarity

                except EmbeddingServiceError as e:
                    logger.warning(f"Error searching for goal {goal['id']}: {e}")
                    continue

        # Search based on asks
        if match_type in ["ask_based", "all"] and user_asks:
            for ask in user_asks:
                if not ask.get("embedding_id"):
                    continue

                try:
                    # Find users who can help with this ask
                    ask_text = f"{ask['description']}"
                    results = await embedding_service.search_similar(
                        query_text=ask_text,
                        entity_type="ask",
                        limit=self.SEARCH_LIMIT_PER_SIGNAL,
                        min_similarity=self.SIMILARITY_THRESHOLD
                    )

                    for result in results:
                        result_user_id = result.get("metadata", {}).get("user_id")
                        if not result_user_id or result_user_id == str(user_id):
                            continue

                        if result_user_id not in candidates_map:
                            candidates_map[result_user_id] = {
                                "user_id": result_user_id,
                                "matching_signals": [],
                                "max_similarity": 0.0
                            }

                        # Track matching signal
                        similarity = result.get("similarity", 0.0)
                        candidates_map[result_user_id]["matching_signals"].append({
                            "type": "ask",
                            "source_id": ask["id"],
                            "source_text": ask["description"],
                            "match_id": result.get("metadata", {}).get("source_id"),
                            "similarity": similarity
                        })

                        # Update max similarity
                        if similarity > candidates_map[result_user_id]["max_similarity"]:
                            candidates_map[result_user_id]["max_similarity"] = similarity

                except EmbeddingServiceError as e:
                    logger.warning(f"Error searching for ask {ask['id']}: {e}")
                    continue

        return list(candidates_map.values())

    async def _score_candidates(
        self,
        user_id: UUID,
        user_goals: List[Dict],
        user_asks: List[Dict],
        candidates: List[Dict],
        min_score: float
    ) -> List[Dict]:
        """
        Calculate detailed scores for each candidate.

        Args:
            user_id: Source user ID
            user_goals: Source user's goals
            user_asks: Source user's asks
            candidates: Candidate users to score
            min_score: Minimum score threshold

        Returns:
            List of scored matches meeting minimum threshold
        """
        scored_matches = []

        for candidate in candidates:
            try:
                # Get candidate user data
                candidate_user = await zerodb_client.get_by_id(
                    table_name="users",
                    id=candidate["user_id"]
                )

                if not candidate_user:
                    continue

                # Check safety - skip scam users
                if await self._is_suspicious_user(candidate_user):
                    logger.warning(f"Skipping suspicious user {candidate['user_id']}")
                    continue

                # Calculate detailed scores
                scores = await self.calculate_match_score(
                    user_a_id=user_id,
                    user_b_id=UUID(candidate["user_id"]),
                    candidate_data=candidate
                )

                # Check if meets minimum threshold
                if scores["overall_score"] < min_score:
                    continue

                # Get candidate goals and asks for reasoning
                candidate_goals = await zerodb_client.query_rows(
                    table_name="goals",
                    filter={"user_id": candidate["user_id"], "is_active": True},
                    limit=5
                )

                candidate_asks = await zerodb_client.query_rows(
                    table_name="asks",
                    filter={"user_id": candidate["user_id"], "status": "open"},
                    limit=5
                )

                # Generate reasoning
                reasoning = await self.generate_match_reasoning(
                    user_goals=user_goals,
                    user_asks=user_asks,
                    candidate_user=candidate_user,
                    candidate_goals=candidate_goals,
                    candidate_asks=candidate_asks,
                    matching_signals=candidate["matching_signals"]
                )

                # Extract matching goals and asks for display
                matching_goals = []
                matching_asks = []

                for signal in candidate["matching_signals"]:
                    if signal["type"] == "goal":
                        matching_goals.append(signal["source_text"][:100])
                    elif signal["type"] == "ask":
                        matching_asks.append(signal["source_text"][:100])

                # Build match result
                scored_matches.append({
                    "target_user_id": candidate["user_id"],
                    "target_name": candidate_user.get("name", "Unknown"),
                    "target_headline": candidate_user.get("headline"),
                    "target_location": candidate_user.get("location"),
                    "match_score": scores,
                    "reasoning": reasoning,
                    "matching_goals": list(set(matching_goals))[:3],
                    "matching_asks": list(set(matching_asks))[:3]
                })

            except Exception as e:
                logger.warning(f"Error scoring candidate {candidate['user_id']}: {e}")
                continue

        return scored_matches

    async def calculate_match_score(
        self,
        user_a_id: UUID,
        user_b_id: UUID,
        candidate_data: Optional[Dict] = None
    ) -> Dict[str, float]:
        """
        Calculate detailed match scores between two users.

        Args:
            user_a_id: First user ID
            user_b_id: Second user ID
            candidate_data: Optional pre-computed candidate data with matching signals

        Returns:
            Dictionary with relevance_score, trust_score, reciprocity_score, overall_score
        """
        # Calculate relevance score (based on semantic similarity)
        relevance_score = await self._calculate_relevance_score(
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            candidate_data=candidate_data
        )

        # Calculate trust score (based on profile completeness and activity)
        trust_score = await self._calculate_trust_score(user_b_id)

        # Calculate reciprocity score (mutual value potential)
        reciprocity_score = await self._calculate_reciprocity_score(
            user_a_id=user_a_id,
            user_b_id=user_b_id
        )

        # Calculate overall weighted score
        overall_score = (
            relevance_score * self.RELEVANCE_WEIGHT +
            trust_score * self.TRUST_WEIGHT +
            reciprocity_score * self.RECIPROCITY_WEIGHT
        )

        return {
            "relevance_score": round(relevance_score, 3),
            "trust_score": round(trust_score, 3),
            "reciprocity_score": round(reciprocity_score, 3),
            "overall_score": round(overall_score, 3)
        }

    async def _calculate_relevance_score(
        self,
        user_a_id: UUID,
        user_b_id: UUID,
        candidate_data: Optional[Dict] = None
    ) -> float:
        """
        Calculate relevance score based on semantic similarity.

        Args:
            user_a_id: First user ID
            user_b_id: Second user ID
            candidate_data: Optional candidate data with matching signals

        Returns:
            Relevance score (0-1)
        """
        if candidate_data and candidate_data.get("matching_signals"):
            # Use max similarity from matching signals
            similarities = [s["similarity"] for s in candidate_data["matching_signals"]]
            avg_similarity = sum(similarities) / len(similarities)
            max_similarity = max(similarities)

            # Weight toward max similarity but consider average
            relevance = (max_similarity * 0.7) + (avg_similarity * 0.3)
            return min(1.0, relevance)

        # Fallback: calculate from scratch if no candidate data
        return 0.5  # Default moderate relevance

    async def _calculate_trust_score(self, user_id: UUID) -> float:
        """
        Calculate trust score based on profile quality and activity.

        Args:
            user_id: User to evaluate

        Returns:
            Trust score (0-1)
        """
        try:
            # Get user profile
            user = await zerodb_client.get_by_id("users", str(user_id))
            if not user:
                return 0.3  # Low trust if user not found

            profile = await zerodb_client.get_by_field(
                "founder_profiles",
                "user_id",
                str(user_id)
            )

            score = 0.0

            # Profile completeness factors (40%)
            if user.get("name"):
                score += 0.1
            if user.get("headline"):
                score += 0.1
            if user.get("location"):
                score += 0.1
            if profile and profile.get("bio"):
                score += 0.1

            # LinkedIn verification (20%)
            if user.get("linkedin_id"):
                score += 0.2

            # Activity level (20%)
            # Check for recent posts
            recent_posts = await zerodb_client.query_rows(
                table_name="posts",
                filter={"user_id": str(user_id)},
                limit=1
            )
            if recent_posts:
                score += 0.2

            # Account age (20%)
            if user.get("created_at"):
                try:
                    created_at = datetime.fromisoformat(user["created_at"].replace("Z", ""))
                    days_old = (datetime.utcnow() - created_at).days
                    # Score increases with age (up to 30 days)
                    score += min(0.2, days_old / 150)
                except Exception:
                    pass

            return min(1.0, score)

        except Exception as e:
            logger.warning(f"Error calculating trust score for {user_id}: {e}")
            return 0.5  # Default moderate trust on error

    async def _calculate_reciprocity_score(
        self,
        user_a_id: UUID,
        user_b_id: UUID
    ) -> float:
        """
        Calculate reciprocity score (mutual value potential).

        Args:
            user_a_id: First user ID
            user_b_id: Second user ID

        Returns:
            Reciprocity score (0-1)
        """
        try:
            # Get both users' goals and asks
            a_goals = await zerodb_client.query_rows(
                table_name="goals",
                filter={"user_id": str(user_a_id), "is_active": True}
            )

            b_goals = await zerodb_client.query_rows(
                table_name="goals",
                filter={"user_id": str(user_b_id), "is_active": True}
            )

            a_asks = await zerodb_client.query_rows(
                table_name="asks",
                filter={"user_id": str(user_a_id), "status": "open"}
            )

            b_asks = await zerodb_client.query_rows(
                table_name="asks",
                filter={"user_id": str(user_b_id), "status": "open"}
            )

            # Both have goals - potential for collaboration
            if a_goals and b_goals:
                return 0.8

            # One has asks, other has goals - potential for help
            if (a_asks and b_goals) or (b_asks and a_goals):
                return 0.7

            # Both have asks - limited reciprocity
            if a_asks and b_asks:
                return 0.4

            # Default moderate reciprocity
            return 0.5

        except Exception as e:
            logger.warning(f"Error calculating reciprocity score: {e}")
            return 0.5

    async def _is_suspicious_user(self, user: Dict) -> bool:
        """
        Check if user appears suspicious (scam/spam).

        Args:
            user: User dictionary

        Returns:
            True if user is suspicious
        """
        try:
            # Check if user has minimal profile info (common spam pattern)
            if not user.get("name") and not user.get("headline"):
                return True

            # Check creation date - very new accounts might be suspicious
            if user.get("created_at"):
                created_at = datetime.fromisoformat(user["created_at"].replace("Z", ""))
                hours_old = (datetime.utcnow() - created_at).total_seconds() / 3600
                if hours_old < 1:  # Created less than 1 hour ago
                    return True

            return False

        except Exception as e:
            logger.warning(f"Error checking user suspicion: {e}")
            return False  # Don't block on errors

    async def generate_match_reasoning(
        self,
        user_goals: List[Dict],
        user_asks: List[Dict],
        candidate_user: Dict,
        candidate_goals: List[Dict],
        candidate_asks: List[Dict],
        matching_signals: List[Dict]
    ) -> str:
        """
        Generate human-readable explanation of why match is good.

        Args:
            user_goals: Source user's goals
            user_asks: Source user's asks
            candidate_user: Target user data
            candidate_goals: Target user's goals
            candidate_asks: Target user's asks
            matching_signals: Matching signals between users

        Returns:
            Human-readable reasoning string
        """
        reasons = []

        # Analyze matching signals
        goal_matches = [s for s in matching_signals if s["type"] == "goal"]
        ask_matches = [s for s in matching_signals if s["type"] == "ask"]

        # Add goal-based reasoning
        if goal_matches:
            top_goal_match = max(goal_matches, key=lambda x: x["similarity"])
            reasons.append(
                f"Working on similar goals: {top_goal_match['source_text'][:80]}"
            )

        # Add ask-based reasoning
        if ask_matches:
            top_ask_match = max(ask_matches, key=lambda x: x["similarity"])
            reasons.append(
                f"Can help with: {top_ask_match['source_text'][:80]}"
            )

        # Add profile-based reasoning
        if candidate_user.get("headline"):
            reasons.append(f"Background: {candidate_user['headline']}")

        # Add location if same
        if candidate_user.get("location"):
            reasons.append(f"Based in {candidate_user['location']}")

        # Combine reasons
        if reasons:
            return ". ".join(reasons) + "."
        else:
            return "Potential valuable connection based on profile similarity."

    async def find_goal_helpers(
        self,
        goal_id: UUID,
        limit: int = 10
    ) -> List[Dict]:
        """
        Find founders who can help with a specific goal.

        Args:
            goal_id: Goal to find helpers for
            limit: Maximum number of helpers to return

        Returns:
            List of potential helper matches
        """
        try:
            # Get goal data
            goal = await zerodb_client.get_by_id("goals", str(goal_id))
            if not goal:
                raise MatchingServiceError(f"Goal {goal_id} not found")

            # Search for similar goals (founders working on similar things)
            goal_text = f"{goal['type']}: {goal['description']}"
            results = await embedding_service.search_similar(
                query_text=goal_text,
                entity_type="goal",
                limit=limit * 2,
                min_similarity=self.SIMILARITY_THRESHOLD
            )

            helpers = []
            for result in results:
                user_id = result.get("metadata", {}).get("user_id")
                if user_id == goal["user_id"]:
                    continue  # Skip goal owner

                # Get helper user data
                helper_user = await zerodb_client.get_by_id("users", user_id)
                if not helper_user:
                    continue

                helpers.append({
                    "user_id": user_id,
                    "name": helper_user.get("name"),
                    "headline": helper_user.get("headline"),
                    "similarity": result.get("similarity", 0.0),
                    "reason": f"Has experience with: {result.get('document', '')[:100]}"
                })

            return helpers[:limit]

        except Exception as e:
            logger.error(f"Error finding goal helpers for {goal_id}: {e}")
            raise MatchingServiceError(f"Failed to find goal helpers: {e}")

    async def find_ask_matchers(
        self,
        ask_id: UUID,
        limit: int = 10
    ) -> List[Dict]:
        """
        Find founders who can fulfill an ask.

        Args:
            ask_id: Ask to find matchers for
            limit: Maximum number of matchers to return

        Returns:
            List of potential matchers
        """
        try:
            # Get ask data
            ask = await zerodb_client.get_by_id("asks", str(ask_id))
            if not ask:
                raise MatchingServiceError(f"Ask {ask_id} not found")

            # Search for similar asks or relevant goals
            ask_text = ask["description"]
            results = await embedding_service.search_similar(
                query_text=ask_text,
                entity_type="goal",  # Search goals for expertise
                limit=limit * 2,
                min_similarity=self.SIMILARITY_THRESHOLD
            )

            matchers = []
            for result in results:
                user_id = result.get("metadata", {}).get("user_id")
                if user_id == ask["user_id"]:
                    continue  # Skip ask creator

                # Get matcher user data
                matcher_user = await zerodb_client.get_by_id("users", user_id)
                if not matcher_user:
                    continue

                matchers.append({
                    "user_id": user_id,
                    "name": matcher_user.get("name"),
                    "headline": matcher_user.get("headline"),
                    "similarity": result.get("similarity", 0.0),
                    "reason": f"Expertise in: {result.get('document', '')[:100]}"
                })

            return matchers[:limit]

        except Exception as e:
            logger.error(f"Error finding ask matchers for {ask_id}: {e}")
            raise MatchingServiceError(f"Failed to find ask matchers: {e}")


# Singleton instance
matching_service = MatchingService()
