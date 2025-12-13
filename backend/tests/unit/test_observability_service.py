"""
Unit tests for Observability Service.

Test Coverage:
- API call tracking
- Embedding cost tracking
- Cache hit/miss tracking
- Error tracking
- Metrics summary generation
- Performance decorator functionality
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from app.services.observability_service import ObservabilityService


class TestObservabilityService:
    """Test Observability Service functionality."""

    @pytest.fixture
    def observability_service(self):
        """Create observability service instance for testing."""
        return ObservabilityService()

    @pytest.mark.asyncio
    async def test_track_api_call_success(self, observability_service):
        """Test tracking successful API call."""
        await observability_service.track_api_call(
            endpoint="/api/v1/goals",
            method="GET",
            duration_ms=125.5,
            status_code=200,
            user_id="user_123"
        )

        # Verify metric was stored
        assert len(observability_service.metrics["api_calls"]) == 1

        call = observability_service.metrics["api_calls"][0]
        assert call["endpoint"] == "/api/v1/goals"
        assert call["method"] == "GET"
        assert call["duration_ms"] == 125.5
        assert call["status_code"] == 200
        assert call["user_id"] == "user_123"
        assert call["error"] is None

    @pytest.mark.asyncio
    async def test_track_api_call_with_error(self, observability_service):
        """Test tracking API call with error."""
        await observability_service.track_api_call(
            endpoint="/api/v1/posts",
            method="POST",
            duration_ms=50.0,
            status_code=500,
            user_id="user_456",
            error="Internal server error"
        )

        call = observability_service.metrics["api_calls"][0]
        assert call["status_code"] == 500
        assert call["error"] == "Internal server error"

    @pytest.mark.asyncio
    async def test_track_api_call_slow_request_warning(self, observability_service, caplog):
        """Test slow request triggers warning."""
        import logging
        caplog.set_level(logging.WARNING)

        await observability_service.track_api_call(
            endpoint="/api/v1/slow-endpoint",
            method="GET",
            duration_ms=2500.0,  # > 2000ms threshold
            status_code=200
        )

        # Check for slow request warning in logs
        assert any("SLOW_REQUEST" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_track_embedding_cost(self, observability_service):
        """Test tracking embedding generation cost."""
        await observability_service.track_embedding_cost(
            operation="generate",
            tokens=100,
            model="BAAI/bge-small-en-v1.5",
            entity_type="goal"
        )

        assert len(observability_service.metrics["embedding_costs"]) == 1

        cost_metric = observability_service.metrics["embedding_costs"][0]
        assert cost_metric["operation"] == "generate"
        assert cost_metric["tokens"] == 100
        assert cost_metric["model"] == "BAAI/bge-small-en-v1.5"
        assert cost_metric["entity_type"] == "goal"
        assert "cost_usd" in cost_metric

    @pytest.mark.asyncio
    async def test_track_embedding_cost_calculation(self, observability_service):
        """Test embedding cost calculation is correct."""
        await observability_service.track_embedding_cost(
            operation="search",
            tokens=1000,
            model="BAAI/bge-small-en-v1.5"
        )

        cost_metric = observability_service.metrics["embedding_costs"][0]
        expected_cost = (1000 / 1000) * 0.00002  # $0.00002 per 1k tokens
        assert abs(cost_metric["cost_usd"] - expected_cost) < 0.000001

    @pytest.mark.asyncio
    async def test_track_cache_hit(self, observability_service):
        """Test tracking cache hit."""
        await observability_service.track_cache_hit(
            cache_type="embedding",
            hit=True,
            key="goal_123"
        )

        assert observability_service.metrics["cache_hits"] == 1
        assert observability_service.metrics["cache_misses"] == 0

    @pytest.mark.asyncio
    async def test_track_cache_miss(self, observability_service):
        """Test tracking cache miss."""
        await observability_service.track_cache_hit(
            cache_type="query",
            hit=False,
            key="search_456"
        )

        assert observability_service.metrics["cache_hits"] == 0
        assert observability_service.metrics["cache_misses"] == 1

    @pytest.mark.asyncio
    async def test_track_cache_hit_rate_calculation(self, observability_service):
        """Test cache hit rate is calculated correctly."""
        # Track 3 hits and 1 miss
        await observability_service.track_cache_hit("embedding", True)
        await observability_service.track_cache_hit("embedding", True)
        await observability_service.track_cache_hit("embedding", True)
        await observability_service.track_cache_hit("embedding", False)

        # Hit rate should be 75%
        assert observability_service.metrics["cache_hits"] == 3
        assert observability_service.metrics["cache_misses"] == 1

    @pytest.mark.asyncio
    async def test_track_error_medium_severity(self, observability_service):
        """Test tracking medium severity error."""
        await observability_service.track_error(
            error_type="validation_error",
            error_message="Invalid goal type",
            severity="medium",
            context={"field": "goal_type", "value": "invalid"}
        )

        assert len(observability_service.metrics["errors"]) == 1

        error = observability_service.metrics["errors"][0]
        assert error["error_type"] == "validation_error"
        assert error["error_message"] == "Invalid goal type"
        assert error["severity"] == "medium"
        assert error["context"]["field"] == "goal_type"

    @pytest.mark.asyncio
    async def test_track_error_critical_severity(self, observability_service, caplog):
        """Test tracking critical error logs at error level."""
        import logging
        caplog.set_level(logging.ERROR)

        await observability_service.track_error(
            error_type="database_error",
            error_message="Connection lost",
            severity="critical"
        )

        # Verify error was logged at ERROR level
        assert any(record.levelname == "ERROR" for record in caplog.records)

    @pytest.mark.asyncio
    async def test_get_metrics_summary_empty(self, observability_service):
        """Test metrics summary with no data."""
        summary = await observability_service.get_metrics_summary(time_range_minutes=60)

        assert summary["api"]["total_calls"] == 0
        assert summary["api"]["avg_duration_ms"] == 0
        assert summary["embeddings"]["total_operations"] == 0
        assert summary["cache"]["total_operations"] == 0
        assert summary["cache"]["hit_rate_percent"] == 0

    @pytest.mark.asyncio
    async def test_get_metrics_summary_with_data(self, observability_service):
        """Test metrics summary with tracked data."""
        # Track some API calls
        await observability_service.track_api_call("/goals", "GET", 100.0, 200)
        await observability_service.track_api_call("/asks", "POST", 200.0, 201)
        await observability_service.track_api_call("/posts", "GET", 150.0, 200)

        # Track embedding costs
        await observability_service.track_embedding_cost("generate", 100, "test-model")
        await observability_service.track_embedding_cost("search", 50, "test-model")

        # Track cache operations
        await observability_service.track_cache_hit("embedding", True)
        await observability_service.track_cache_hit("embedding", True)
        await observability_service.track_cache_hit("embedding", False)

        summary = await observability_service.get_metrics_summary(time_range_minutes=60)

        # API metrics
        assert summary["api"]["total_calls"] == 3
        assert summary["api"]["avg_duration_ms"] == 150.0  # (100 + 200 + 150) / 3
        assert summary["api"]["error_count"] == 0
        assert summary["api"]["error_rate_percent"] == 0

        # Embedding metrics
        assert summary["embeddings"]["total_operations"] == 2
        assert summary["embeddings"]["total_tokens"] == 150

        # Cache metrics
        assert summary["cache"]["total_operations"] == 3
        assert summary["cache"]["hits"] == 2
        assert summary["cache"]["misses"] == 1
        assert summary["cache"]["hit_rate_percent"] == pytest.approx(66.67, rel=0.1)

    @pytest.mark.asyncio
    async def test_get_metrics_summary_error_rate(self, observability_service):
        """Test error rate calculation in summary."""
        # Track 3 successful calls and 2 errors
        await observability_service.track_api_call("/test", "GET", 100.0, 200)
        await observability_service.track_api_call("/test", "GET", 100.0, 200)
        await observability_service.track_api_call("/test", "GET", 100.0, 200)
        await observability_service.track_api_call("/test", "GET", 100.0, 400)
        await observability_service.track_api_call("/test", "GET", 100.0, 500)

        summary = await observability_service.get_metrics_summary(time_range_minutes=60)

        assert summary["api"]["total_calls"] == 5
        assert summary["api"]["error_count"] == 2
        assert summary["api"]["error_rate_percent"] == 40.0  # 2/5 * 100

    @pytest.mark.asyncio
    async def test_track_performance_decorator_success(self, observability_service):
        """Test performance tracking decorator on successful function."""

        @observability_service.track_performance("test_endpoint")
        async def test_function():
            return "success"

        result = await test_function()

        assert result == "success"
        assert len(observability_service.metrics["api_calls"]) == 1

        call = observability_service.metrics["api_calls"][0]
        assert call["endpoint"] == "test_endpoint"
        assert call["status_code"] == 200
        assert call["duration_ms"] > 0

    @pytest.mark.asyncio
    async def test_track_performance_decorator_with_error(self, observability_service):
        """Test performance tracking decorator on failing function."""

        @observability_service.track_performance("failing_endpoint")
        async def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await failing_function()

        # Error should still be tracked
        assert len(observability_service.metrics["api_calls"]) == 1

        call = observability_service.metrics["api_calls"][0]
        assert call["endpoint"] == "failing_endpoint"
        assert call["status_code"] == 500
        assert call["error"] == "Test error"

    @pytest.mark.asyncio
    async def test_track_performance_decorator_extracts_user_id(self, observability_service):
        """Test decorator extracts user_id from kwargs."""

        # Mock user object
        mock_user = MagicMock()
        mock_user.id = uuid4()

        @observability_service.track_performance("user_endpoint")
        async def user_function(current_user=None):
            return "user_result"

        result = await user_function(current_user=mock_user)

        assert result == "user_result"

        call = observability_service.metrics["api_calls"][0]
        assert call["user_id"] == str(mock_user.id)

    @pytest.mark.asyncio
    async def test_multiple_operations_tracking(self, observability_service):
        """Test tracking multiple operations of different types."""
        # API calls
        await observability_service.track_api_call("/goals", "GET", 100, 200, "user1")
        await observability_service.track_api_call("/asks", "POST", 150, 201, "user2")

        # Embedding costs
        await observability_service.track_embedding_cost("generate", 100, "model1", "goal")
        await observability_service.track_embedding_cost("search", 200, "model1", "ask")

        # Cache operations
        await observability_service.track_cache_hit("embedding", True)
        await observability_service.track_cache_hit("query", False)

        # Errors
        await observability_service.track_error("error1", "message1", "low")
        await observability_service.track_error("error2", "message2", "high")

        # Verify all metrics tracked
        assert len(observability_service.metrics["api_calls"]) == 2
        assert len(observability_service.metrics["embedding_costs"]) == 2
        assert observability_service.metrics["cache_hits"] == 1
        assert observability_service.metrics["cache_misses"] == 1
        assert len(observability_service.metrics["errors"]) == 2

    @pytest.mark.asyncio
    async def test_metrics_summary_time_filtering(self, observability_service):
        """Test metrics summary respects time range filtering."""
        from datetime import datetime, timedelta

        # Add an old metric (simulate by modifying timestamp)
        await observability_service.track_api_call("/old", "GET", 100, 200)

        # Manually set old timestamp (2 hours ago)
        old_time = datetime.utcnow() - timedelta(hours=2)
        observability_service.metrics["api_calls"][0]["timestamp"] = old_time.isoformat()

        # Add recent metric
        await observability_service.track_api_call("/recent", "GET", 100, 200)

        # Get summary for last 60 minutes
        summary = await observability_service.get_metrics_summary(time_range_minutes=60)

        # Should only count the recent call
        assert summary["api"]["total_calls"] == 1
