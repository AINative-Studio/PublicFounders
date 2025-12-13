"""
Observability Service - Track API performance, costs, and usage metrics.

This service provides:
1. API endpoint performance tracking
2. Embedding generation cost monitoring
3. Cache hit/miss rate tracking
4. Error rate and latency metrics
5. User activity tracking

Architecture:
- Logging-based initially (can integrate with external observability platforms later)
- Decorator-based performance tracking for easy integration
- Structured logging for easy parsing
- Non-blocking async operations
"""
import time
import logging
from typing import Dict, Any, Optional
from functools import wraps
from datetime import datetime
from uuid import UUID
import json

logger = logging.getLogger(__name__)


class ObservabilityService:
    """
    Manages observability tracking for API performance and costs.

    Features:
    - API endpoint latency tracking
    - Embedding cost tracking (tokens/operations)
    - Cache performance monitoring
    - Error tracking and alerting
    - User activity metrics
    """

    def __init__(self):
        """Initialize observability service."""
        # Metrics storage (in-memory for now, can switch to Redis/TimeSeries DB)
        self.metrics = {
            "api_calls": [],
            "embedding_costs": [],
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": []
        }

        # Embedding cost estimation
        self.EMBEDDING_COST_PER_1K_TOKENS = 0.00002  # Free for HuggingFace models via AINative
        self.AVG_TOKENS_PER_REQUEST = 50

    async def track_api_call(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int,
        user_id: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Track API call metrics.

        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            duration_ms: Request duration in milliseconds
            status_code: HTTP status code
            user_id: Optional user ID
            error: Optional error message
        """
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "endpoint": endpoint,
            "method": method,
            "duration_ms": duration_ms,
            "status_code": status_code,
            "user_id": user_id,
            "error": error
        }

        # Store metric
        self.metrics["api_calls"].append(metric)

        # Structured logging for external tools to parse
        log_message = (
            f"API_METRIC | "
            f"endpoint={endpoint} | "
            f"method={method} | "
            f"duration_ms={duration_ms:.2f} | "
            f"status={status_code} | "
            f"user={user_id or 'anonymous'}"
        )

        if error:
            log_message += f" | error={error}"

        # Log at appropriate level
        if status_code >= 500:
            logger.error(log_message)
        elif status_code >= 400:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # Alert on slow requests (> 2 seconds)
        if duration_ms > 2000:
            logger.warning(
                f"SLOW_REQUEST | {endpoint} took {duration_ms:.2f}ms | "
                f"Consider optimization"
            )

    async def track_embedding_cost(
        self,
        operation: str,
        tokens: int,
        model: str = "BAAI/bge-small-en-v1.5",
        entity_type: Optional[str] = None
    ) -> None:
        """
        Track embedding API usage and estimated costs.

        Args:
            operation: Operation type (generate, search)
            tokens: Number of tokens processed
            model: Embedding model used
            entity_type: Optional entity type (goal, ask, post)
        """
        cost = (tokens / 1000) * self.EMBEDDING_COST_PER_1K_TOKENS

        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "tokens": tokens,
            "model": model,
            "cost_usd": cost,
            "entity_type": entity_type
        }

        self.metrics["embedding_costs"].append(metric)

        logger.info(
            f"EMBEDDING_COST | "
            f"operation={operation} | "
            f"tokens={tokens} | "
            f"model={model} | "
            f"cost=${cost:.6f} | "
            f"entity={entity_type or 'N/A'}"
        )

    async def track_cache_hit(
        self,
        cache_type: str,
        hit: bool,
        key: Optional[str] = None
    ) -> None:
        """
        Track cache hit/miss rates.

        Args:
            cache_type: Type of cache (embedding, query, session)
            hit: True if cache hit, False if miss
            key: Optional cache key (for debugging)
        """
        if hit:
            self.metrics["cache_hits"] += 1
        else:
            self.metrics["cache_misses"] += 1

        # Calculate hit rate
        total = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        hit_rate = (self.metrics["cache_hits"] / total * 100) if total > 0 else 0

        logger.info(
            f"CACHE_METRIC | "
            f"type={cache_type} | "
            f"hit={hit} | "
            f"key={key or 'N/A'} | "
            f"hit_rate={hit_rate:.2f}%"
        )

    async def track_error(
        self,
        error_type: str,
        error_message: str,
        severity: str = "medium",
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track application errors for monitoring.

        Args:
            error_type: Error type/category
            error_message: Error message
            severity: Error severity (low, medium, high, critical)
            context: Additional error context
        """
        error = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "severity": severity,
            "context": context or {}
        }

        self.metrics["errors"].append(error)

        # Log with appropriate level
        if severity in ["high", "critical"]:
            logger.error(
                f"ERROR | "
                f"type={error_type} | "
                f"severity={severity} | "
                f"message={error_message} | "
                f"context={json.dumps(context or {})}"
            )
        else:
            logger.warning(
                f"ERROR | "
                f"type={error_type} | "
                f"severity={severity} | "
                f"message={error_message}"
            )

    async def get_metrics_summary(
        self,
        time_range_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Get summary of recent metrics.

        Args:
            time_range_minutes: Time range for summary in minutes

        Returns:
            Dictionary with metrics summary
        """
        now = datetime.utcnow()
        cutoff_time = now.timestamp() - (time_range_minutes * 60)

        # Filter recent API calls
        recent_calls = [
            call for call in self.metrics["api_calls"]
            if datetime.fromisoformat(call["timestamp"]).timestamp() > cutoff_time
        ]

        # Calculate API metrics
        total_calls = len(recent_calls)
        avg_duration = sum(c["duration_ms"] for c in recent_calls) / total_calls if total_calls > 0 else 0
        error_count = sum(1 for c in recent_calls if c["status_code"] >= 400)
        error_rate = (error_count / total_calls * 100) if total_calls > 0 else 0

        # Calculate embedding costs
        recent_costs = [
            cost for cost in self.metrics["embedding_costs"]
            if datetime.fromisoformat(cost["timestamp"]).timestamp() > cutoff_time
        ]
        total_cost = sum(c["cost_usd"] for c in recent_costs)
        total_tokens = sum(c["tokens"] for c in recent_costs)

        # Cache metrics
        total_cache_ops = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        cache_hit_rate = (
            (self.metrics["cache_hits"] / total_cache_ops * 100)
            if total_cache_ops > 0
            else 0
        )

        summary = {
            "time_range_minutes": time_range_minutes,
            "api": {
                "total_calls": total_calls,
                "avg_duration_ms": round(avg_duration, 2),
                "error_count": error_count,
                "error_rate_percent": round(error_rate, 2)
            },
            "embeddings": {
                "total_operations": len(recent_costs),
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 6)
            },
            "cache": {
                "total_operations": total_cache_ops,
                "hits": self.metrics["cache_hits"],
                "misses": self.metrics["cache_misses"],
                "hit_rate_percent": round(cache_hit_rate, 2)
            }
        }

        return summary

    def track_performance(self, endpoint_name: str):
        """
        Decorator for tracking endpoint performance.

        Usage:
            @observability_service.track_performance("goals_search")
            async def search_goals(...):
                ...

        Args:
            endpoint_name: Name of the endpoint for tracking
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                error = None
                status_code = 200

                try:
                    result = await func(*args, **kwargs)
                    return result

                except Exception as e:
                    error = str(e)
                    status_code = 500
                    raise

                finally:
                    duration_ms = (time.time() - start_time) * 1000

                    # Extract user_id if available in kwargs
                    user_id = None
                    if "current_user" in kwargs:
                        user = kwargs["current_user"]
                        user_id = str(user.id) if hasattr(user, "id") else None

                    # Track the API call
                    await self.track_api_call(
                        endpoint=endpoint_name,
                        method="API",
                        duration_ms=duration_ms,
                        status_code=status_code,
                        user_id=user_id,
                        error=error
                    )

            return wrapper
        return decorator


# Singleton instance
observability_service = ObservabilityService()
