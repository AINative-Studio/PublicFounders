"""
Monitoring Service - Health checks and alerting for introduction matching system.

This service monitors the RLHF data pipeline and matching algorithm for:
- Performance degradation
- Data quality issues
- Anomaly detection
- System health

Alerts are triggered when metrics deviate from expected baselines.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.services.analytics_service import analytics_service, AnalyticsServiceError
from app.services.rlhf_service import rlhf_service, RLHFServiceError
from app.services.zerodb_client import zerodb_client

logger = logging.getLogger(__name__)


class MonitoringServiceError(Exception):
    """Base exception for monitoring service errors."""
    pass


class AlertSeverity:
    """Alert severity levels."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MonitoringService:
    """
    Monitors matching algorithm performance and data quality.

    Key Responsibilities:
    - Daily metrics health checks
    - Anomaly detection (sudden drops in success rate)
    - Data quality validation
    - RLHF collection health monitoring
    - Alert generation and logging
    """

    # Thresholds for alerts
    MIN_SUCCESS_RATE = 0.4  # Alert if below 40%
    MIN_RESPONSE_RATE = 0.3  # Alert if below 30%
    MIN_DAILY_VOLUME = 5  # Alert if < 5 intros per day
    MAX_DATA_QUALITY_ISSUES_PCT = 0.1  # Alert if > 10% have issues

    # Anomaly detection
    SUCCESS_RATE_DROP_THRESHOLD = 0.15  # Alert if 15%+ drop from baseline
    RESPONSE_TIME_INCREASE_THRESHOLD = 1.5  # Alert if 50%+ increase in response time

    def __init__(self):
        """Initialize monitoring service."""
        self.alerts_table = "monitoring_alerts"
        self.baseline_cache = {}

    async def run_daily_health_check(self) -> Dict[str, Any]:
        """
        Run comprehensive daily health check of the matching system.

        This should be scheduled to run daily (e.g., via cron or scheduler).

        Returns:
            Dict with health check results and any alerts generated
        """
        logger.info("Running daily health check")

        try:
            health_report = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "healthy",
                "checks": [],
                "alerts": []
            }

            # Check 1: Overall metrics health
            metrics_check = await self._check_overall_metrics()
            health_report["checks"].append(metrics_check)
            if metrics_check.get("alerts"):
                health_report["alerts"].extend(metrics_check["alerts"])

            # Check 2: Success rate trends
            trend_check = await self._check_success_rate_trends()
            health_report["checks"].append(trend_check)
            if trend_check.get("alerts"):
                health_report["alerts"].extend(trend_check["alerts"])

            # Check 3: Data quality
            quality_check = await self._check_data_quality()
            health_report["checks"].append(quality_check)
            if quality_check.get("alerts"):
                health_report["alerts"].extend(quality_check["alerts"])

            # Check 4: RLHF collection health
            rlhf_check = await self._check_rlhf_health()
            health_report["checks"].append(rlhf_check)
            if rlhf_check.get("alerts"):
                health_report["alerts"].extend(rlhf_check["alerts"])

            # Check 5: Volume monitoring
            volume_check = await self._check_volume_health()
            health_report["checks"].append(volume_check)
            if volume_check.get("alerts"):
                health_report["alerts"].extend(volume_check["alerts"])

            # Determine overall status
            if any(alert["severity"] in [AlertSeverity.CRITICAL, AlertSeverity.HIGH] for alert in health_report["alerts"]):
                health_report["status"] = "unhealthy"
            elif any(alert["severity"] == AlertSeverity.MEDIUM for alert in health_report["alerts"]):
                health_report["status"] = "degraded"

            # Log all alerts
            for alert in health_report["alerts"]:
                await self._log_alert(alert)

            logger.info(f"Health check complete: status={health_report['status']}, alerts={len(health_report['alerts'])}")

            return health_report

        except Exception as e:
            logger.error(f"Error during health check: {e}")
            raise MonitoringServiceError(f"Health check failed: {e}")

    async def _check_overall_metrics(self) -> Dict[str, Any]:
        """Check if overall metrics are within healthy ranges."""
        try:
            metrics = await analytics_service.get_overall_metrics(time_range="day")

            check = {
                "name": "overall_metrics",
                "status": "pass",
                "metrics": {
                    "success_rate": metrics.get("success_rate"),
                    "response_rate": metrics.get("response_rate"),
                    "total_introductions": metrics.get("total_introductions")
                },
                "alerts": []
            }

            # Check success rate
            success_rate = metrics.get("success_rate", 0.0)
            if success_rate < self.MIN_SUCCESS_RATE:
                check["status"] = "fail"
                check["alerts"].append({
                    "severity": AlertSeverity.HIGH,
                    "type": "low_success_rate",
                    "message": f"Success rate dropped to {success_rate:.1%} (threshold: {self.MIN_SUCCESS_RATE:.1%})",
                    "metric": "success_rate",
                    "value": success_rate,
                    "threshold": self.MIN_SUCCESS_RATE
                })

            # Check response rate
            response_rate = metrics.get("response_rate", 0.0)
            if response_rate < self.MIN_RESPONSE_RATE:
                check["status"] = "fail"
                check["alerts"].append({
                    "severity": AlertSeverity.MEDIUM,
                    "type": "low_response_rate",
                    "message": f"Response rate dropped to {response_rate:.1%} (threshold: {self.MIN_RESPONSE_RATE:.1%})",
                    "metric": "response_rate",
                    "value": response_rate,
                    "threshold": self.MIN_RESPONSE_RATE
                })

            return check

        except AnalyticsServiceError as e:
            logger.error(f"Failed to check overall metrics: {e}")
            return {
                "name": "overall_metrics",
                "status": "error",
                "error": str(e),
                "alerts": [{
                    "severity": AlertSeverity.CRITICAL,
                    "type": "metrics_unavailable",
                    "message": f"Failed to retrieve metrics: {e}"
                }]
            }

    async def _check_success_rate_trends(self) -> Dict[str, Any]:
        """Detect anomalies in success rate trends."""
        try:
            # Get recent trends
            trends = await analytics_service.get_temporal_trends(days=14)

            check = {
                "name": "success_rate_trends",
                "status": "pass",
                "trend": trends.get("trend"),
                "alerts": []
            }

            # Get baseline (average of first week)
            daily_metrics = trends.get("daily_metrics", [])
            if len(daily_metrics) < 7:
                check["status"] = "insufficient_data"
                return check

            first_week = daily_metrics[:7]
            last_3_days = daily_metrics[-3:]

            baseline_success = sum(d["success_rate"] for d in first_week) / 7
            recent_success = sum(d["success_rate"] for d in last_3_days) / 3

            # Check for significant drop
            if baseline_success > 0:
                drop = (baseline_success - recent_success) / baseline_success

                if drop > self.SUCCESS_RATE_DROP_THRESHOLD:
                    check["status"] = "fail"
                    check["alerts"].append({
                        "severity": AlertSeverity.HIGH,
                        "type": "success_rate_drop",
                        "message": f"Success rate dropped {drop:.1%} from baseline ({baseline_success:.1%} → {recent_success:.1%})",
                        "baseline": baseline_success,
                        "current": recent_success,
                        "drop_pct": drop
                    })

            # Check trend
            if trends.get("trend") == "declining":
                check["alerts"].append({
                    "severity": AlertSeverity.MEDIUM,
                    "type": "declining_trend",
                    "message": "Success rate showing declining trend over past 14 days"
                })

            return check

        except Exception as e:
            logger.error(f"Failed to check trends: {e}")
            return {
                "name": "success_rate_trends",
                "status": "error",
                "error": str(e),
                "alerts": []
            }

    async def _check_data_quality(self) -> Dict[str, Any]:
        """Check for data quality issues in RLHF tracking."""
        try:
            # Get recent introductions
            start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()

            intros = await zerodb_client.query_rows(
                table_name="introductions",
                filter={"created_at": {"$gte": start_date}},
                limit=1000
            )

            check = {
                "name": "data_quality",
                "status": "pass",
                "total_introductions": len(intros),
                "issues": {
                    "missing_context": 0,
                    "missing_match_scores": 0,
                    "missing_outcomes": 0,
                    "invalid_scores": 0
                },
                "alerts": []
            }

            if not intros:
                check["status"] = "no_data"
                return check

            # Check each introduction for data quality issues
            for intro in intros:
                # Check for missing context
                if not intro.get("context"):
                    check["issues"]["missing_context"] += 1

                # Check for missing match scores
                match_scores = intro.get("context", {}).get("match_scores", {})
                if not match_scores or not all(k in match_scores for k in ["relevance", "trust", "reciprocity", "overall"]):
                    check["issues"]["missing_match_scores"] += 1

                # Check for invalid score ranges
                for score_name, score_value in match_scores.items():
                    if not (0.0 <= score_value <= 1.0):
                        check["issues"]["invalid_scores"] += 1
                        break

                # Check for missing outcomes (completed intros should have outcomes)
                if intro.get("status") == "completed" and not intro.get("outcome"):
                    check["issues"]["missing_outcomes"] += 1

            # Calculate issue percentage
            total_issues = sum(check["issues"].values())
            issue_pct = total_issues / len(intros) if intros else 0.0

            if issue_pct > self.MAX_DATA_QUALITY_ISSUES_PCT:
                check["status"] = "fail"
                check["alerts"].append({
                    "severity": AlertSeverity.MEDIUM,
                    "type": "data_quality_issues",
                    "message": f"{issue_pct:.1%} of introductions have data quality issues (threshold: {self.MAX_DATA_QUALITY_ISSUES_PCT:.1%})",
                    "issue_pct": issue_pct,
                    "issues": check["issues"]
                })

            return check

        except Exception as e:
            logger.error(f"Failed to check data quality: {e}")
            return {
                "name": "data_quality",
                "status": "error",
                "error": str(e),
                "alerts": []
            }

    async def _check_rlhf_health(self) -> Dict[str, Any]:
        """Check RLHF data collection health."""
        try:
            # Get RLHF insights
            insights = await rlhf_service.get_rlhf_insights(time_range="day")

            check = {
                "name": "rlhf_health",
                "status": "pass",
                "rlhf_interactions": insights.get("total_interactions", 0),
                "avg_feedback": insights.get("avg_feedback", 0.0),
                "alerts": []
            }

            # Check if RLHF is collecting data
            total_interactions = insights.get("total_interactions", 0)
            if total_interactions == 0:
                check["status"] = "fail"
                check["alerts"].append({
                    "severity": AlertSeverity.HIGH,
                    "type": "rlhf_not_collecting",
                    "message": "No RLHF interactions recorded in past 24 hours"
                })

            # Check avg feedback score
            avg_feedback = insights.get("avg_feedback", 0.0)
            if avg_feedback < 0.0:
                check["alerts"].append({
                    "severity": AlertSeverity.MEDIUM,
                    "type": "negative_feedback",
                    "message": f"Average feedback score is negative: {avg_feedback:.2f}"
                })

            return check

        except RLHFServiceError as e:
            logger.error(f"Failed to check RLHF health: {e}")
            return {
                "name": "rlhf_health",
                "status": "error",
                "error": str(e),
                "alerts": [{
                    "severity": AlertSeverity.CRITICAL,
                    "type": "rlhf_service_error",
                    "message": f"RLHF service unavailable: {e}"
                }]
            }

    async def _check_volume_health(self) -> Dict[str, Any]:
        """Check if introduction volume is healthy."""
        try:
            metrics = await analytics_service.get_overall_metrics(time_range="day")

            total = metrics.get("total_introductions", 0)

            check = {
                "name": "volume_health",
                "status": "pass",
                "daily_volume": total,
                "alerts": []
            }

            # Check if volume is too low
            if total < self.MIN_DAILY_VOLUME:
                check["status"] = "warning"
                check["alerts"].append({
                    "severity": AlertSeverity.LOW,
                    "type": "low_volume",
                    "message": f"Low introduction volume: {total} introductions in past 24h (threshold: {self.MIN_DAILY_VOLUME})",
                    "daily_volume": total,
                    "threshold": self.MIN_DAILY_VOLUME
                })

            return check

        except Exception as e:
            logger.error(f"Failed to check volume: {e}")
            return {
                "name": "volume_health",
                "status": "error",
                "error": str(e),
                "alerts": []
            }

    async def _log_alert(self, alert: Dict[str, Any]) -> None:
        """Log alert to monitoring_alerts table."""
        try:
            alert_record = {
                "id": str(UUID(int=0)),  # Will be auto-generated
                "timestamp": datetime.utcnow().isoformat(),
                "severity": alert.get("severity"),
                "type": alert.get("type"),
                "message": alert.get("message"),
                "details": alert,
                "acknowledged": False,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            # Log to console
            log_level = logging.WARNING
            if alert["severity"] == AlertSeverity.CRITICAL:
                log_level = logging.CRITICAL
            elif alert["severity"] == AlertSeverity.HIGH:
                log_level = logging.ERROR
            elif alert["severity"] == AlertSeverity.MEDIUM:
                log_level = logging.WARNING

            logger.log(log_level, f"ALERT: {alert['message']}")

            # Would also insert to database for persistence
            # await zerodb_client.insert_rows(self.alerts_table, [alert_record])

        except Exception as e:
            logger.error(f"Failed to log alert: {e}")

    async def get_alert_history(
        self,
        days: int = 7,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get alert history.

        Args:
            days: Number of days to look back
            severity: Optional filter by severity

        Returns:
            List of alerts
        """
        try:
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

            filter_query = {"timestamp": {"$gte": start_date}}
            if severity:
                filter_query["severity"] = severity

            alerts = await zerodb_client.query_rows(
                table_name=self.alerts_table,
                filter=filter_query,
                limit=1000,
                sort={"timestamp": -1}
            )

            return alerts

        except Exception as e:
            logger.error(f"Failed to get alert history: {e}")
            return []

    async def check_anomaly_in_metric(
        self,
        metric_name: str,
        current_value: float,
        baseline_value: float,
        threshold_pct: float = 0.2
    ) -> Optional[Dict[str, Any]]:
        """
        Generic anomaly detection for any metric.

        Args:
            metric_name: Name of the metric
            current_value: Current metric value
            baseline_value: Expected/baseline value
            threshold_pct: Percentage deviation threshold (default 20%)

        Returns:
            Alert dict if anomaly detected, None otherwise
        """
        if baseline_value == 0:
            return None

        deviation = abs(current_value - baseline_value) / baseline_value

        if deviation > threshold_pct:
            severity = AlertSeverity.HIGH if deviation > 0.5 else AlertSeverity.MEDIUM

            return {
                "severity": severity,
                "type": "metric_anomaly",
                "metric": metric_name,
                "message": f"{metric_name} anomaly: {deviation:.1%} deviation from baseline",
                "current_value": current_value,
                "baseline_value": baseline_value,
                "deviation_pct": deviation
            }

        return None

    async def get_system_health_summary(self) -> Dict[str, Any]:
        """
        Get quick system health summary.

        Returns:
            Dict with health status and key metrics
        """
        try:
            # Get recent health check
            health_check = await self.run_daily_health_check()

            # Get recent alerts
            recent_alerts = await self.get_alert_history(days=1)

            summary = {
                "status": health_check["status"],
                "timestamp": datetime.utcnow().isoformat(),
                "alerts_24h": len(recent_alerts),
                "critical_alerts_24h": sum(1 for a in recent_alerts if a.get("severity") == AlertSeverity.CRITICAL),
                "health_checks": {
                    check["name"]: check["status"]
                    for check in health_check["checks"]
                }
            }

            return summary

        except Exception as e:
            logger.error(f"Failed to get health summary: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Singleton instance
monitoring_service = MonitoringService()
