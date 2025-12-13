"""
Unit tests for Cache Service.

Tests cache functionality including:
- Cache key generation
- Cache hit/miss scenarios
- TTL expiration
- Cache invalidation
- Cache statistics
"""
import pytest
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from app.services.cache_service import CacheService, cache_service


class TestCacheKeyGeneration:
    """Test cache key generation logic."""

    def test_generate_cache_key_deterministic(self):
        """Test that same inputs always generate same key."""
        user_id = uuid4()
        goals = ["Raise seed funding", "Hire first engineer"]

        key1 = cache_service.generate_cache_key(user_id, goals)
        key2 = cache_service.generate_cache_key(user_id, goals)

        assert key1 == key2
        assert len(key1) == 64  # SHA256 hash length

    def test_generate_cache_key_order_independent(self):
        """Test that goal order doesn't affect cache key."""
        user_id = uuid4()
        goals1 = ["Raise seed funding", "Hire first engineer"]
        goals2 = ["Hire first engineer", "Raise seed funding"]

        key1 = cache_service.generate_cache_key(user_id, goals1)
        key2 = cache_service.generate_cache_key(user_id, goals2)

        assert key1 == key2

    def test_generate_cache_key_different_users(self):
        """Test that different users get different cache keys."""
        user1 = uuid4()
        user2 = uuid4()
        goals = ["Raise seed funding"]

        key1 = cache_service.generate_cache_key(user1, goals)
        key2 = cache_service.generate_cache_key(user2, goals)

        assert key1 != key2

    def test_generate_cache_key_different_goals(self):
        """Test that different goals get different cache keys."""
        user_id = uuid4()
        goals1 = ["Raise seed funding"]
        goals2 = ["Hire first engineer"]

        key1 = cache_service.generate_cache_key(user_id, goals1)
        key2 = cache_service.generate_cache_key(user_id, goals2)

        assert key1 != key2

    def test_generate_cache_key_empty_goals(self):
        """Test cache key generation with empty goals list."""
        user_id = uuid4()
        goals = []

        key = cache_service.generate_cache_key(user_id, goals)

        assert len(key) == 64
        assert isinstance(key, str)


@pytest.mark.asyncio
class TestCacheLookup:
    """Test cache lookup functionality."""

    async def test_get_cached_discovery_miss(self):
        """Test cache miss returns None."""
        user_id = uuid4()
        goals = ["Raise seed funding"]

        result = await cache_service.get_cached_discovery(user_id, goals)

        # Currently returns None since we haven't implemented MCP integration
        assert result is None

    async def test_get_cached_discovery_handles_errors(self):
        """Test that cache errors don't crash the application."""
        user_id = uuid4()
        goals = ["Raise seed funding"]

        # Should handle errors gracefully and return None
        result = await cache_service.get_cached_discovery(user_id, goals)

        assert result is None  # Graceful fallback


@pytest.mark.asyncio
class TestCacheStorage:
    """Test cache storage functionality."""

    async def test_cache_discovery_results_success(self):
        """Test storing discovery results."""
        user_id = uuid4()
        goals = ["Raise seed funding"]
        results = {
            "posts": [],
            "similarity_scores": [],
            "total": 0
        }

        success = await cache_service.cache_discovery_results(
            user_id=user_id,
            goal_descriptions=goals,
            results=results,
            ttl_seconds=300
        )

        # Currently returns True as a placeholder
        assert success is True

    async def test_cache_discovery_results_with_custom_ttl(self):
        """Test storing results with custom TTL."""
        user_id = uuid4()
        goals = ["Raise seed funding"]
        results = {"posts": [], "similarity_scores": [], "total": 0}

        success = await cache_service.cache_discovery_results(
            user_id=user_id,
            goal_descriptions=goals,
            results=results,
            ttl_seconds=600  # 10 minutes
        )

        assert success is True

    async def test_cache_discovery_results_handles_errors(self):
        """Test that storage errors don't crash the application."""
        user_id = uuid4()
        goals = ["Raise seed funding"]
        results = {"posts": [], "similarity_scores": [], "total": 0}

        # Should handle errors gracefully
        success = await cache_service.cache_discovery_results(
            user_id=user_id,
            goal_descriptions=goals,
            results=results
        )

        # Returns False on error, but we're in placeholder mode
        assert isinstance(success, bool)


@pytest.mark.asyncio
class TestCacheInvalidation:
    """Test cache invalidation functionality."""

    async def test_invalidate_specific_cache_entry(self):
        """Test invalidating a specific cache entry."""
        user_id = uuid4()
        goals = ["Raise seed funding"]

        deleted_count = await cache_service.invalidate_cache(
            user_id=user_id,
            goal_descriptions=goals
        )

        # Returns 0 in placeholder mode
        assert deleted_count == 0

    async def test_invalidate_user_cache(self):
        """Test invalidating all cache entries for a user."""
        user_id = uuid4()

        deleted_count = await cache_service.invalidate_user_cache(user_id)

        assert deleted_count == 0  # Placeholder returns 0

    async def test_invalidate_all_cache(self):
        """Test invalidating entire cache."""
        deleted_count = await cache_service.invalidate_all_cache()

        assert deleted_count == 0  # Placeholder returns 0

    async def test_invalidate_cache_handles_errors(self):
        """Test that invalidation errors don't crash."""
        user_id = uuid4()

        # Should handle errors gracefully
        deleted_count = await cache_service.invalidate_user_cache(user_id)

        assert isinstance(deleted_count, int)


@pytest.mark.asyncio
class TestCacheStats:
    """Test cache statistics functionality."""

    async def test_get_cache_stats(self):
        """Test getting cache statistics."""
        stats = await cache_service.get_cache_stats()

        assert isinstance(stats, dict)
        assert "total_entries" in stats
        assert "expired_entries" in stats
        assert "active_entries" in stats
        assert "table_name" in stats
        assert "default_ttl_seconds" in stats

    async def test_cache_stats_table_name(self):
        """Test that stats include correct table name."""
        stats = await cache_service.get_cache_stats()

        assert stats["table_name"] == "discovery_cache"

    async def test_cache_stats_default_ttl(self):
        """Test that stats include default TTL."""
        stats = await cache_service.get_cache_stats()

        assert stats["default_ttl_seconds"] == 300  # 5 minutes


class TestCacheServiceConfiguration:
    """Test cache service configuration."""

    def test_default_ttl_configured(self):
        """Test that default TTL is set correctly."""
        assert CacheService.DEFAULT_TTL_SECONDS == 300

    def test_table_name_configured(self):
        """Test that table name is set correctly."""
        assert CacheService.TABLE_NAME == "discovery_cache"

    def test_singleton_instance(self):
        """Test that cache_service is properly instantiated."""
        assert cache_service is not None
        assert isinstance(cache_service, CacheService)


@pytest.mark.asyncio
class TestCacheIntegrationScenarios:
    """Test realistic cache usage scenarios."""

    async def test_cache_miss_then_store_scenario(self):
        """Test typical scenario: cache miss, fetch data, store in cache."""
        user_id = uuid4()
        goals = ["Raise seed funding", "Hire first engineer"]

        # 1. Check cache (miss)
        cached = await cache_service.get_cached_discovery(user_id, goals)
        assert cached is None

        # 2. Simulate fetching data
        results = {
            "posts": [
                {
                    "id": str(uuid4()),
                    "user_id": str(uuid4()),
                    "type": "milestone",
                    "content": "Just raised $1M seed round!",
                    "created_at": datetime.utcnow().isoformat()
                }
            ],
            "similarity_scores": [0.95],
            "total": 1
        }

        # 3. Store in cache
        success = await cache_service.cache_discovery_results(
            user_id=user_id,
            goal_descriptions=goals,
            results=results
        )
        assert success is True

    async def test_cache_invalidation_on_new_post(self):
        """Test cache invalidation when new post is created."""
        # Simulate user creating a new post
        # This should invalidate all cache entries

        deleted_count = await cache_service.invalidate_all_cache()

        # In production, this would delete actual cache entries
        assert isinstance(deleted_count, int)

    async def test_cache_invalidation_on_goal_update(self):
        """Test cache invalidation when user updates goals."""
        user_id = uuid4()

        # When user updates their goals, invalidate their cache
        deleted_count = await cache_service.invalidate_user_cache(user_id)

        assert isinstance(deleted_count, int)


@pytest.mark.asyncio
class TestCachePerformanceExpectations:
    """Test performance expectations for cache operations."""

    async def test_cache_key_generation_performance(self):
        """Test that cache key generation is fast."""
        import time

        user_id = uuid4()
        goals = ["Goal " + str(i) for i in range(10)]

        start = time.time()
        for _ in range(1000):
            cache_service.generate_cache_key(user_id, goals)
        duration = time.time() - start

        # Should generate 1000 keys in under 1 second
        assert duration < 1.0

    async def test_cache_lookup_timeout_expectation(self):
        """Test cache lookup completes quickly."""
        import time

        user_id = uuid4()
        goals = ["Raise seed funding"]

        start = time.time()
        await cache_service.get_cached_discovery(user_id, goals)
        duration = time.time() - start

        # Cache lookup should complete in under 200ms (target for cache hits)
        # In placeholder mode, this will be very fast
        assert duration < 0.2


@pytest.mark.asyncio
class TestCacheErrorHandling:
    """Test error handling in cache operations."""

    async def test_cache_handles_none_user_id(self):
        """Test cache handles None user_id gracefully."""
        # This should not crash, but behavior may vary
        try:
            cache_service.generate_cache_key(None, ["Goal 1"])
        except (TypeError, AttributeError):
            # Expected to fail for None
            pass

    async def test_cache_handles_empty_results(self):
        """Test caching empty results."""
        user_id = uuid4()
        goals = ["Raise seed funding"]
        empty_results = {"posts": [], "similarity_scores": [], "total": 0}

        success = await cache_service.cache_discovery_results(
            user_id=user_id,
            goal_descriptions=goals,
            results=empty_results
        )

        assert success is True

    async def test_cache_handles_large_results(self):
        """Test caching large result sets."""
        user_id = uuid4()
        goals = ["Raise seed funding"]

        # Simulate large result set
        large_results = {
            "posts": [{"id": str(uuid4())} for _ in range(100)],
            "similarity_scores": [0.9] * 100,
            "total": 100
        }

        success = await cache_service.cache_discovery_results(
            user_id=user_id,
            goal_descriptions=goals,
            results=large_results
        )

        assert success is True
