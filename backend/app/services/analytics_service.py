"""
Analytics Service - Introduction matching quality analytics and dashboards.

This service provides comprehensive analytics for Epic 8: Outcomes & Learning.
It analyzes introduction outcomes to surface insights about matching quality,
success patterns, and opportunities for algorithm improvement.

Key Metrics:
- Overall success rate
- Success rate by match score range
- Success rate by goal type
- Success rate by industry match
- Average time to outcome
- Response rate (accepted / requested)
- Completion rate (completed / accepted)
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.services.zerodb_client import zerodb_client
from app.services.rlhf_service import rlhf_service

logger = logging.getLogger(__name__)


class AnalyticsServiceError(Exception):
    """Base exception for analytics service errors."""
    pass


class AnalyticsService:
    """
    Provides analytics dashboards and metrics for introduction matching.

    Analyzes RLHF data and introduction outcomes to track:
    - Success rates across various dimensions
    - Match quality distribution
    - Temporal patterns
    - User segments performance
    """

    def __init__(self):
        """Initialize analytics service."""
        self.table_name = "introductions"

    async def get_overall_metrics(
        self,
        time_range: str = "week"
    ) -> Dict[str, Any]:
        """
        Get overall introduction matching metrics.

        Args:
            time_range: Time range for analysis (day, week, month, all)

        Returns:
            Dict with comprehensive metrics
        """
        try:
            logger.info(f"Calculating overall metrics for time_range: {time_range}")

            # Get time filter
            start_date = self._get_start_date(time_range)

            # Query introductions
            filter_query = {}
            if start_date:
                filter_query["created_at"] = {"$gte": start_date}

            intros = await zerodb_client.query_rows(
                table_name=self.table_name,
                filter=filter_query,
                limit=10000  # Reasonable limit for analytics
            )

            # Calculate core metrics
            total = len(intros)
            if total == 0:
                return self._empty_metrics_response(time_range)

            # Status breakdown
            status_counts = self._count_by_field(intros, "status")

            # Success metrics
            successful = self._count_successful(intros)
            accepted = status_counts.get("accepted", 0) + status_counts.get("completed", 0)
            completed = status_counts.get("completed", 0)

            # Calculate rates
            success_rate = successful / total if total > 0 else 0.0
            response_rate = (accepted + status_counts.get("declined", 0)) / total if total > 0 else 0.0
            acceptance_rate = accepted / total if total > 0 else 0.0
            completion_rate = completed / accepted if accepted > 0 else 0.0

            # Timing metrics
            avg_time_to_response = await self._calculate_avg_time_to_response(intros)
            avg_time_to_completion = await self._calculate_avg_time_to_completion(intros)

            # Rating metrics
            avg_rating, rating_dist = await self._calculate_rating_metrics(intros)

            # Get RLHF quality metrics
            rlhf_metrics = await rlhf_service.get_matching_quality_metrics(time_range)

            metrics = {
                "time_range": time_range,
                "start_date": start_date,
                "generated_at": datetime.utcnow().isoformat(),

                # Volume metrics
                "total_introductions": total,
                "total_unique_users": await self._count_unique_users(intros),

                # Status breakdown
                "status_breakdown": status_counts,

                # Core success metrics
                "success_rate": round(success_rate, 3),
                "response_rate": round(response_rate, 3),
                "acceptance_rate": round(acceptance_rate, 3),
                "completion_rate": round(completion_rate, 3),

                # Absolute counts
                "successful_introductions": successful,
                "accepted_introductions": accepted,
                "declined_introductions": status_counts.get("declined", 0),
                "expired_introductions": status_counts.get("expired", 0),

                # Timing metrics
                "avg_time_to_response_hours": round(avg_time_to_response, 1),
                "avg_time_to_completion_days": round(avg_time_to_completion, 1),

                # Rating metrics
                "avg_rating": round(avg_rating, 2) if avg_rating else None,
                "rating_distribution": rating_dist,

                # RLHF metrics
                "avg_feedback_score": rlhf_metrics.get("avg_feedback_score", 0.0),
                "rlhf_success_rate": rlhf_metrics.get("success_rate", 0.0)
            }

            logger.info(f"Calculated overall metrics: success_rate={success_rate:.2%}")
            return metrics

        except Exception as e:
            logger.error(f"Error calculating overall metrics: {e}")
            raise AnalyticsServiceError(f"Failed to calculate metrics: {e}")

    async def get_success_rate_by_score_range(
        self,
        time_range: str = "week"
    ) -> Dict[str, Any]:
        """
        Analyze success rate by match score ranges.

        This helps answer: "Do higher match scores lead to more successful introductions?"

        Args:
            time_range: Time range for analysis

        Returns:
            Dict with success rates for each score bucket
        """
        try:
            logger.info("Calculating success rate by match score range")

            # Get introductions with context
            start_date = self._get_start_date(time_range)
            filter_query = {}
            if start_date:
                filter_query["created_at"] = {"$gte": start_date}

            intros = await zerodb_client.query_rows(
                table_name=self.table_name,
                filter=filter_query,
                limit=10000
            )

            if not intros:
                return {"error": "No data available", "score_ranges": []}

            # Define score buckets
            score_buckets = {
                "0.90-1.00": (0.90, 1.00),
                "0.80-0.90": (0.80, 0.90),
                "0.70-0.80": (0.70, 0.80),
                "0.60-0.70": (0.60, 0.70),
                "0.50-0.60": (0.50, 0.60),
                "< 0.50": (0.0, 0.50)
            }

            # Group intros by score bucket
            bucket_intros = defaultdict(list)

            for intro in intros:
                overall_score = intro.get("context", {}).get("match_scores", {}).get("overall", 0.0)

                # Find appropriate bucket
                for bucket_name, (min_score, max_score) in score_buckets.items():
                    if min_score <= overall_score < max_score or (bucket_name == "0.90-1.00" and overall_score == 1.0):
                        bucket_intros[bucket_name].append(intro)
                        break

            # Calculate metrics for each bucket
            bucket_metrics = []
            for bucket_name in score_buckets.keys():
                bucket_data = bucket_intros.get(bucket_name, [])
                total = len(bucket_data)

                if total == 0:
                    bucket_metrics.append({
                        "score_range": bucket_name,
                        "total": 0,
                        "success_rate": 0.0,
                        "acceptance_rate": 0.0,
                        "completion_rate": 0.0
                    })
                    continue

                successful = self._count_successful(bucket_data)
                accepted = sum(1 for i in bucket_data if i.get("status") in ["accepted", "completed"])
                completed = sum(1 for i in bucket_data if i.get("status") == "completed")

                bucket_metrics.append({
                    "score_range": bucket_name,
                    "total": total,
                    "success_rate": round(successful / total, 3),
                    "acceptance_rate": round(accepted / total, 3),
                    "completion_rate": round(completed / accepted, 3) if accepted > 0 else 0.0,
                    "avg_score": round(
                        sum(i.get("context", {}).get("match_scores", {}).get("overall", 0.0) for i in bucket_data) / total,
                        3
                    )
                })

            # Calculate trend (higher scores = higher success?)
            correlation = self._calculate_score_success_correlation(bucket_metrics)

            result = {
                "time_range": time_range,
                "score_ranges": bucket_metrics,
                "correlation": round(correlation, 3) if correlation else None,
                "insight": self._generate_score_insight(bucket_metrics, correlation),
                "generated_at": datetime.utcnow().isoformat()
            }

            return result

        except Exception as e:
            logger.error(f"Error calculating success by score range: {e}")
            raise AnalyticsServiceError(f"Failed to calculate score range metrics: {e}")

    async def get_success_rate_by_goal_type(
        self,
        time_range: str = "week"
    ) -> Dict[str, Any]:
        """
        Analyze success rate by goal type combinations.

        This helps answer: "Which goal type pairings work best?"

        Args:
            time_range: Time range for analysis

        Returns:
            Dict with success rates for each goal type combination
        """
        try:
            logger.info("Calculating success rate by goal type")

            start_date = self._get_start_date(time_range)
            filter_query = {}
            if start_date:
                filter_query["created_at"] = {"$gte": start_date}

            intros = await zerodb_client.query_rows(
                table_name=self.table_name,
                filter=filter_query,
                limit=10000
            )

            if not intros:
                return {"error": "No data available", "goal_types": []}

            # Group by goal type
            goal_type_intros = defaultdict(list)

            for intro in intros:
                goal_types = intro.get("context", {}).get("matching_context", {}).get("goal_types", [])

                # Primary goal type (first one)
                primary_goal = goal_types[0] if goal_types else "unknown"
                goal_type_intros[primary_goal].append(intro)

                # Also track if multiple goal types
                if len(goal_types) > 1:
                    goal_type_intros["multi_goal"].append(intro)

            # Calculate metrics for each goal type
            goal_type_metrics = []
            for goal_type, goal_intros in goal_type_intros.items():
                total = len(goal_intros)
                successful = self._count_successful(goal_intros)
                accepted = sum(1 for i in goal_intros if i.get("status") in ["accepted", "completed"])

                goal_type_metrics.append({
                    "goal_type": goal_type,
                    "total": total,
                    "success_rate": round(successful / total, 3),
                    "acceptance_rate": round(accepted / total, 3),
                    "avg_match_score": round(
                        sum(i.get("context", {}).get("match_scores", {}).get("overall", 0.0) for i in goal_intros) / total,
                        3
                    )
                })

            # Sort by success rate
            goal_type_metrics.sort(key=lambda x: x["success_rate"], reverse=True)

            result = {
                "time_range": time_range,
                "goal_types": goal_type_metrics,
                "top_performing": goal_type_metrics[0] if goal_type_metrics else None,
                "worst_performing": goal_type_metrics[-1] if goal_type_metrics else None,
                "generated_at": datetime.utcnow().isoformat()
            }

            return result

        except Exception as e:
            logger.error(f"Error calculating success by goal type: {e}")
            raise AnalyticsServiceError(f"Failed to calculate goal type metrics: {e}")

    async def get_success_rate_by_industry_match(
        self,
        time_range: str = "week"
    ) -> Dict[str, Any]:
        """
        Compare success rates for same-industry vs cross-industry introductions.

        This helps answer: "Does industry match matter for success?"

        Args:
            time_range: Time range for analysis

        Returns:
            Dict comparing industry match vs no match
        """
        try:
            logger.info("Calculating success rate by industry match")

            start_date = self._get_start_date(time_range)
            filter_query = {}
            if start_date:
                filter_query["created_at"] = {"$gte": start_date}

            intros = await zerodb_client.query_rows(
                table_name=self.table_name,
                filter=filter_query,
                limit=10000
            )

            if not intros:
                return {"error": "No data available"}

            # Split by industry match
            industry_match_intros = []
            no_industry_match_intros = []

            for intro in intros:
                industry_match = intro.get("context", {}).get("matching_context", {}).get("industry_match", False)

                if industry_match:
                    industry_match_intros.append(intro)
                else:
                    no_industry_match_intros.append(intro)

            # Calculate metrics for each group
            def calculate_group_metrics(group_intros, label):
                total = len(group_intros)
                if total == 0:
                    return {
                        "label": label,
                        "total": 0,
                        "success_rate": 0.0,
                        "acceptance_rate": 0.0,
                        "avg_match_score": 0.0
                    }

                successful = self._count_successful(group_intros)
                accepted = sum(1 for i in group_intros if i.get("status") in ["accepted", "completed"])

                return {
                    "label": label,
                    "total": total,
                    "success_rate": round(successful / total, 3),
                    "acceptance_rate": round(accepted / total, 3),
                    "avg_match_score": round(
                        sum(i.get("context", {}).get("match_scores", {}).get("overall", 0.0) for i in group_intros) / total,
                        3
                    )
                }

            match_metrics = calculate_group_metrics(industry_match_intros, "Industry Match")
            no_match_metrics = calculate_group_metrics(no_industry_match_intros, "No Industry Match")

            # Calculate lift
            lift = None
            if no_match_metrics["success_rate"] > 0:
                lift = (match_metrics["success_rate"] - no_match_metrics["success_rate"]) / no_match_metrics["success_rate"]

            result = {
                "time_range": time_range,
                "with_industry_match": match_metrics,
                "without_industry_match": no_match_metrics,
                "lift": round(lift, 3) if lift else None,
                "lift_pct": f"{lift * 100:+.1f}%" if lift else None,
                "insight": self._generate_industry_match_insight(match_metrics, no_match_metrics, lift),
                "generated_at": datetime.utcnow().isoformat()
            }

            return result

        except Exception as e:
            logger.error(f"Error calculating industry match metrics: {e}")
            raise AnalyticsServiceError(f"Failed to calculate industry match metrics: {e}")

    async def get_success_rate_by_match_type(
        self,
        time_range: str = "week"
    ) -> Dict[str, Any]:
        """
        Compare success rates for goal-based, ask-based, and hybrid matches.

        Args:
            time_range: Time range for analysis

        Returns:
            Dict comparing match type success rates
        """
        try:
            logger.info("Calculating success rate by match type")

            start_date = self._get_start_date(time_range)
            filter_query = {}
            if start_date:
                filter_query["created_at"] = {"$gte": start_date}

            intros = await zerodb_client.query_rows(
                table_name=self.table_name,
                filter=filter_query,
                limit=10000
            )

            if not intros:
                return {"error": "No data available", "match_types": []}

            # Group by match type
            match_type_groups = defaultdict(list)

            for intro in intros:
                match_type = intro.get("context", {}).get("matching_context", {}).get("match_type", "unknown")
                match_type_groups[match_type].append(intro)

            # Calculate metrics for each type
            match_type_metrics = []
            for match_type, type_intros in match_type_groups.items():
                total = len(type_intros)
                successful = self._count_successful(type_intros)
                accepted = sum(1 for i in type_intros if i.get("status") in ["accepted", "completed"])

                match_type_metrics.append({
                    "match_type": match_type,
                    "total": total,
                    "success_rate": round(successful / total, 3),
                    "acceptance_rate": round(accepted / total, 3),
                    "avg_match_score": round(
                        sum(i.get("context", {}).get("match_scores", {}).get("overall", 0.0) for i in type_intros) / total,
                        3
                    )
                })

            # Sort by success rate
            match_type_metrics.sort(key=lambda x: x["success_rate"], reverse=True)

            result = {
                "time_range": time_range,
                "match_types": match_type_metrics,
                "best_performing": match_type_metrics[0] if match_type_metrics else None,
                "generated_at": datetime.utcnow().isoformat()
            }

            return result

        except Exception as e:
            logger.error(f"Error calculating match type metrics: {e}")
            raise AnalyticsServiceError(f"Failed to calculate match type metrics: {e}")

    async def get_temporal_trends(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze temporal trends in introduction success rates.

        Args:
            days: Number of days to analyze

        Returns:
            Dict with daily success rate trends
        """
        try:
            logger.info(f"Calculating temporal trends for {days} days")

            # Get introductions from last N days
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

            intros = await zerodb_client.query_rows(
                table_name=self.table_name,
                filter={"created_at": {"$gte": start_date}},
                limit=10000,
                sort={"created_at": 1}
            )

            if not intros:
                return {"error": "No data available", "daily_metrics": []}

            # Group by day
            daily_groups = defaultdict(list)

            for intro in intros:
                created_at = datetime.fromisoformat(intro["created_at"].replace("Z", ""))
                day_key = created_at.date().isoformat()
                daily_groups[day_key].append(intro)

            # Calculate metrics for each day
            daily_metrics = []
            for day in sorted(daily_groups.keys()):
                day_intros = daily_groups[day]
                total = len(day_intros)
                successful = self._count_successful(day_intros)
                accepted = sum(1 for i in day_intros if i.get("status") in ["accepted", "completed"])

                daily_metrics.append({
                    "date": day,
                    "total": total,
                    "success_rate": round(successful / total, 3) if total > 0 else 0.0,
                    "acceptance_rate": round(accepted / total, 3) if total > 0 else 0.0,
                    "successful_count": successful
                })

            # Calculate trend (improving vs declining)
            trend = self._calculate_trend(daily_metrics)

            result = {
                "days_analyzed": days,
                "start_date": start_date,
                "daily_metrics": daily_metrics,
                "trend": trend,
                "avg_daily_volume": round(len(intros) / days, 1),
                "generated_at": datetime.utcnow().isoformat()
            }

            return result

        except Exception as e:
            logger.error(f"Error calculating temporal trends: {e}")
            raise AnalyticsServiceError(f"Failed to calculate temporal trends: {e}")

    async def get_user_segment_performance(
        self,
        time_range: str = "month"
    ) -> Dict[str, Any]:
        """
        Analyze success rates across user segments.

        Segments:
        - New users (< 30 days old)
        - Active users (> 5 introductions)
        - Highly connected (> 10 introductions)

        Args:
            time_range: Time range for analysis

        Returns:
            Dict with segment performance metrics
        """
        try:
            logger.info("Calculating user segment performance")

            start_date = self._get_start_date(time_range)
            filter_query = {}
            if start_date:
                filter_query["created_at"] = {"$gte": start_date}

            intros = await zerodb_client.query_rows(
                table_name=self.table_name,
                filter=filter_query,
                limit=10000
            )

            if not intros:
                return {"error": "No data available", "segments": []}

            # Get user stats
            user_stats = await self._calculate_user_stats(intros)

            # Define segments
            segments = {
                "new_users": [],
                "active_users": [],
                "power_users": []
            }

            for intro in intros:
                requester_id = intro["requester_id"]
                stats = user_stats.get(requester_id, {})

                account_age_days = stats.get("account_age_days", 0)
                total_intros = stats.get("total_intros", 0)

                # Categorize
                if account_age_days < 30:
                    segments["new_users"].append(intro)
                if total_intros > 5:
                    segments["active_users"].append(intro)
                if total_intros > 10:
                    segments["power_users"].append(intro)

            # Calculate metrics for each segment
            segment_metrics = []
            for segment_name, segment_intros in segments.items():
                total = len(segment_intros)
                if total == 0:
                    continue

                successful = self._count_successful(segment_intros)
                accepted = sum(1 for i in segment_intros if i.get("status") in ["accepted", "completed"])

                segment_metrics.append({
                    "segment": segment_name,
                    "total": total,
                    "success_rate": round(successful / total, 3),
                    "acceptance_rate": round(accepted / total, 3),
                    "avg_match_score": round(
                        sum(i.get("context", {}).get("match_scores", {}).get("overall", 0.0) for i in segment_intros) / total,
                        3
                    )
                })

            result = {
                "time_range": time_range,
                "segments": segment_metrics,
                "generated_at": datetime.utcnow().isoformat()
            }

            return result

        except Exception as e:
            logger.error(f"Error calculating segment performance: {e}")
            raise AnalyticsServiceError(f"Failed to calculate segment performance: {e}")

    async def get_comprehensive_dashboard(
        self,
        time_range: str = "week"
    ) -> Dict[str, Any]:
        """
        Get all analytics in one comprehensive dashboard view.

        Args:
            time_range: Time range for analysis

        Returns:
            Dict with all analytics combined
        """
        try:
            logger.info(f"Generating comprehensive dashboard for {time_range}")

            # Run all analytics in parallel would be ideal, but for simplicity, sequential is fine
            overall = await self.get_overall_metrics(time_range)
            by_score = await self.get_success_rate_by_score_range(time_range)
            by_goal = await self.get_success_rate_by_goal_type(time_range)
            by_industry = await self.get_success_rate_by_industry_match(time_range)
            by_match_type = await self.get_success_rate_by_match_type(time_range)

            dashboard = {
                "time_range": time_range,
                "generated_at": datetime.utcnow().isoformat(),

                # Overall metrics
                "overall": overall,

                # Dimensional analysis
                "by_score_range": by_score,
                "by_goal_type": by_goal,
                "by_industry_match": by_industry,
                "by_match_type": by_match_type,

                # Key insights
                "insights": self._generate_dashboard_insights(
                    overall, by_score, by_goal, by_industry, by_match_type
                )
            }

            return dashboard

        except Exception as e:
            logger.error(f"Error generating dashboard: {e}")
            raise AnalyticsServiceError(f"Failed to generate dashboard: {e}")

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _get_start_date(self, time_range: str) -> Optional[str]:
        """Get start date based on time range."""
        if time_range == "all":
            return None
        elif time_range == "day":
            start = datetime.utcnow() - timedelta(days=1)
        elif time_range == "week":
            start = datetime.utcnow() - timedelta(days=7)
        elif time_range == "month":
            start = datetime.utcnow() - timedelta(days=30)
        elif time_range == "quarter":
            start = datetime.utcnow() - timedelta(days=90)
        else:
            start = datetime.utcnow() - timedelta(days=7)  # Default to week

        return start.isoformat()

    def _count_by_field(self, intros: List[Dict], field: str) -> Dict[str, int]:
        """Count introductions by field value."""
        counts = defaultdict(int)
        for intro in intros:
            value = intro.get(field, "unknown")
            counts[value] += 1
        return dict(counts)

    def _count_successful(self, intros: List[Dict]) -> int:
        """
        Count successful introductions.

        Success defined as:
        - Status = "completed" with positive outcome, OR
        - High RLHF feedback score (> 0.6)
        """
        successful = 0
        for intro in intros:
            status = intro.get("status")
            outcome = intro.get("outcome")

            # Check if completed with positive outcome
            if status == "completed" and outcome in ["meeting_scheduled", "email_exchanged"]:
                successful += 1
            # Or accepted (partial success)
            elif status == "accepted":
                successful += 1

        return successful

    async def _count_unique_users(self, intros: List[Dict]) -> int:
        """Count unique users involved in introductions."""
        user_ids = set()
        for intro in intros:
            user_ids.add(intro.get("requester_id"))
            user_ids.add(intro.get("target_id"))
        return len(user_ids)

    async def _calculate_avg_time_to_response(self, intros: List[Dict]) -> float:
        """Calculate average time from request to response."""
        times = []
        for intro in intros:
            if intro.get("responded_at") and intro.get("requested_at"):
                try:
                    requested = datetime.fromisoformat(intro["requested_at"].replace("Z", ""))
                    responded = datetime.fromisoformat(intro["responded_at"].replace("Z", ""))
                    hours = (responded - requested).total_seconds() / 3600
                    times.append(hours)
                except Exception:
                    continue

        return sum(times) / len(times) if times else 0.0

    async def _calculate_avg_time_to_completion(self, intros: List[Dict]) -> float:
        """Calculate average time from request to completion."""
        times = []
        for intro in intros:
            if intro.get("completed_at") and intro.get("requested_at"):
                try:
                    requested = datetime.fromisoformat(intro["requested_at"].replace("Z", ""))
                    completed = datetime.fromisoformat(intro["completed_at"].replace("Z", ""))
                    days = (completed - requested).total_seconds() / 86400
                    times.append(days)
                except Exception:
                    continue

        return sum(times) / len(times) if times else 0.0

    async def _calculate_rating_metrics(self, intros: List[Dict]) -> Tuple[Optional[float], Dict[int, int]]:
        """Calculate average rating and distribution."""
        ratings = []
        rating_dist = defaultdict(int)

        for intro in intros:
            # Rating might be in outcome data or context
            rating = intro.get("context", {}).get("rating")
            if rating:
                ratings.append(rating)
                rating_dist[rating] += 1

        avg_rating = sum(ratings) / len(ratings) if ratings else None
        return avg_rating, dict(rating_dist)

    async def _calculate_user_stats(self, intros: List[Dict]) -> Dict[str, Dict[str, Any]]:
        """Calculate stats for each user involved in introductions."""
        user_stats = defaultdict(lambda: {"total_intros": 0, "account_age_days": 0})

        # Count intros per user
        for intro in intros:
            requester_id = intro["requester_id"]
            target_id = intro["target_id"]

            user_stats[requester_id]["total_intros"] += 1
            user_stats[target_id]["total_intros"] += 1

        # Get account ages (would query users table in real implementation)
        # For now, placeholder
        for user_id in user_stats:
            try:
                user = await zerodb_client.get_by_id("users", user_id)
                if user and user.get("created_at"):
                    created = datetime.fromisoformat(user["created_at"].replace("Z", ""))
                    age_days = (datetime.utcnow() - created).days
                    user_stats[user_id]["account_age_days"] = age_days
            except Exception:
                continue

        return dict(user_stats)

    def _calculate_score_success_correlation(self, bucket_metrics: List[Dict]) -> Optional[float]:
        """Calculate correlation between score and success rate."""
        if len(bucket_metrics) < 2:
            return None

        # Simple linear correlation
        scores = [m["avg_score"] for m in bucket_metrics]
        success_rates = [m["success_rate"] for m in bucket_metrics]

        # Pearson correlation
        try:
            import numpy as np
            correlation = np.corrcoef(scores, success_rates)[0, 1]
            return correlation
        except Exception:
            # Fallback: just check if trend is positive
            return 1.0 if success_rates[-1] > success_rates[0] else -1.0

    def _calculate_trend(self, daily_metrics: List[Dict]) -> str:
        """Determine if metrics are improving, declining, or stable."""
        if len(daily_metrics) < 7:
            return "insufficient_data"

        # Compare first week to last week
        first_week = daily_metrics[:7]
        last_week = daily_metrics[-7:]

        avg_first = sum(d["success_rate"] for d in first_week) / 7
        avg_last = sum(d["success_rate"] for d in last_week) / 7

        if avg_last > avg_first * 1.05:
            return "improving"
        elif avg_last < avg_first * 0.95:
            return "declining"
        else:
            return "stable"

    def _generate_score_insight(self, bucket_metrics: List[Dict], correlation: Optional[float]) -> str:
        """Generate insight about score-success relationship."""
        if not bucket_metrics or correlation is None:
            return "Insufficient data to generate insights"

        if correlation > 0.7:
            return "Strong positive correlation: Higher match scores consistently lead to more successful introductions"
        elif correlation > 0.3:
            return "Moderate positive correlation: Match scores are predictive of success but other factors matter"
        elif correlation > -0.3:
            return "Weak correlation: Match scores alone are not strongly predictive of success"
        else:
            return "Negative correlation: Review matching algorithm - higher scores may not guarantee success"

    def _generate_industry_match_insight(
        self,
        match_metrics: Dict,
        no_match_metrics: Dict,
        lift: Optional[float]
    ) -> str:
        """Generate insight about industry match impact."""
        if lift is None or lift == 0:
            return "No significant difference between industry match and no match"

        if lift > 0.2:
            return f"Strong positive impact: Industry match increases success by {lift*100:.0f}%"
        elif lift > 0.1:
            return f"Moderate positive impact: Industry match provides {lift*100:.0f}% lift"
        elif lift > 0:
            return f"Small positive impact: Industry match helps slightly ({lift*100:.0f}% lift)"
        elif lift < -0.1:
            return "Negative impact: Cross-industry introductions may perform better"
        else:
            return "Minimal impact from industry matching"

    def _generate_dashboard_insights(
        self,
        overall: Dict,
        by_score: Dict,
        by_goal: Dict,
        by_industry: Dict,
        by_match_type: Dict
    ) -> List[str]:
        """Generate key insights from all analytics."""
        insights = []

        # Overall performance
        success_rate = overall.get("success_rate", 0.0)
        if success_rate > 0.7:
            insights.append(f"Excellent overall performance with {success_rate:.1%} success rate")
        elif success_rate > 0.5:
            insights.append(f"Good overall performance with {success_rate:.1%} success rate")
        else:
            insights.append(f"Room for improvement: {success_rate:.1%} success rate")

        # Best goal type
        if by_goal.get("top_performing"):
            top_goal = by_goal["top_performing"]
            insights.append(
                f"Best performing goal type: {top_goal['goal_type']} "
                f"({top_goal['success_rate']:.1%} success rate)"
            )

        # Industry match impact
        if by_industry.get("lift_pct"):
            insights.append(f"Industry match impact: {by_industry['lift_pct']} lift")

        # Best match type
        if by_match_type.get("best_performing"):
            best_type = by_match_type["best_performing"]
            insights.append(
                f"Most effective match type: {best_type['match_type']} "
                f"({best_type['success_rate']:.1%} success)"
            )

        return insights

    def _empty_metrics_response(self, time_range: str) -> Dict[str, Any]:
        """Return empty metrics when no data available."""
        return {
            "time_range": time_range,
            "total_introductions": 0,
            "success_rate": 0.0,
            "response_rate": 0.0,
            "acceptance_rate": 0.0,
            "completion_rate": 0.0,
            "error": "No data available for this time range"
        }


# Singleton instance
analytics_service = AnalyticsService()
