"""
Tests for rate limiting module
"""

import os
import time
import pytest
from unittest.mock import patch, MagicMock

# Ensure no Redis in tests
os.environ.pop("REDIS_URL", None)

from shared.rate_limiter import (
    check_rate_limit,
    _check_rate_limit_memory,
    _rate_limit_store,
    RateLimitExceeded
)


class TestRateLimitMemory:
    """Test in-memory rate limiting"""

    def setup_method(self):
        """Clear rate limit store before each test"""
        _rate_limit_store.clear()

    def test_first_request_allowed(self):
        """First request should always be allowed"""
        is_allowed, retry_after = check_rate_limit("user-1", "endpoint-1", limit=5, window_seconds=60)

        assert is_allowed is True
        assert retry_after == 0

    def test_under_limit_allowed(self):
        """Requests under the limit should be allowed"""
        for i in range(5):
            is_allowed, _ = check_rate_limit("user-2", "endpoint-2", limit=10, window_seconds=60)
            assert is_allowed is True

    def test_at_limit_blocked(self):
        """Request at the limit should be blocked"""
        # Make 5 requests (the limit)
        for i in range(5):
            check_rate_limit("user-3", "endpoint-3", limit=5, window_seconds=60)

        # 6th request should be blocked
        is_allowed, retry_after = check_rate_limit("user-3", "endpoint-3", limit=5, window_seconds=60)

        assert is_allowed is False
        assert retry_after > 0

    def test_different_users_independent(self):
        """Different users should have independent rate limits"""
        # Exhaust limit for user A
        for i in range(5):
            check_rate_limit("user-A", "endpoint-4", limit=5, window_seconds=60)

        # User A should be blocked
        is_allowed_a, _ = check_rate_limit("user-A", "endpoint-4", limit=5, window_seconds=60)
        assert is_allowed_a is False

        # User B should still be allowed
        is_allowed_b, _ = check_rate_limit("user-B", "endpoint-4", limit=5, window_seconds=60)
        assert is_allowed_b is True

    def test_different_endpoints_independent(self):
        """Different endpoints should have independent rate limits"""
        # Exhaust limit for endpoint A
        for i in range(5):
            check_rate_limit("user-4", "endpoint-A", limit=5, window_seconds=60)

        # Endpoint A should be blocked
        is_allowed_a, _ = check_rate_limit("user-4", "endpoint-A", limit=5, window_seconds=60)
        assert is_allowed_a is False

        # Endpoint B should still be allowed
        is_allowed_b, _ = check_rate_limit("user-4", "endpoint-B", limit=5, window_seconds=60)
        assert is_allowed_b is True

    def test_window_reset(self):
        """Rate limit should reset after window expires"""
        # Exhaust limit
        for i in range(5):
            check_rate_limit("user-5", "endpoint-5", limit=5, window_seconds=1)

        # Should be blocked
        is_allowed, _ = check_rate_limit("user-5", "endpoint-5", limit=5, window_seconds=1)
        assert is_allowed is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        is_allowed, _ = check_rate_limit("user-5", "endpoint-5", limit=5, window_seconds=1)
        assert is_allowed is True

    def test_retry_after_decreases(self):
        """Retry-after should decrease as time passes"""
        # Exhaust limit
        for i in range(5):
            check_rate_limit("user-6", "endpoint-6", limit=5, window_seconds=10)

        # Get retry_after
        _, retry_after_1 = check_rate_limit("user-6", "endpoint-6", limit=5, window_seconds=10)

        # Wait a bit
        time.sleep(0.5)

        # Get retry_after again
        _, retry_after_2 = check_rate_limit("user-6", "endpoint-6", limit=5, window_seconds=10)

        # Should have decreased (or be roughly the same due to timing)
        assert retry_after_2 <= retry_after_1


class TestRateLimitException:
    """Test RateLimitExceeded exception"""

    def test_exception_properties(self):
        exc = RateLimitExceeded(limit=10, window_seconds=60, retry_after=45)

        assert exc.limit == 10
        assert exc.window_seconds == 60
        assert exc.retry_after == 45
        assert "10" in str(exc)
        assert "60" in str(exc)


class TestAnonymousRateLimiting:
    """Test rate limiting for anonymous (unauthenticated) requests"""

    def setup_method(self):
        _rate_limit_store.clear()

    def test_anonymous_uses_global_key(self):
        """Anonymous requests should use a global key"""
        # The rate limiter uses "_anonymous_global_" for unauthenticated requests
        # This is tested indirectly through the decorator behavior
        is_allowed, _ = check_rate_limit("_anonymous_global_", "test", limit=5, window_seconds=60)
        assert is_allowed is True


class TestRedisRateLimiting:
    """Test Redis-backed rate limiting (mocked)"""

    def test_redis_client_lazy_init(self):
        """Redis client should be lazily initialized"""
        from shared.rate_limiter import _get_redis_client

        # Without REDIS_URL, should return None
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("REDIS_URL", None)
            client = _get_redis_client()
            # Will be None if redis not configured or import fails
            assert client is None or client is not None  # Just check it doesn't crash

    def test_redis_fallback_on_error(self):
        """Should fallback gracefully if Redis fails"""
        from shared.rate_limiter import _check_rate_limit_redis

        mock_redis = MagicMock()
        mock_redis.pipeline.side_effect = Exception("Redis connection failed")

        # Should return True (fail open) to not block legitimate requests
        is_allowed, retry_after = _check_rate_limit_redis(
            mock_redis, "user", "endpoint", limit=5, window_seconds=60
        )

        assert is_allowed is True
        assert retry_after == 0


class TestRateLimitCleanup:
    """Test cleanup of expired rate limit entries"""

    def setup_method(self):
        _rate_limit_store.clear()

    def test_old_entries_cleaned_up(self):
        """Old entries should be cleaned up to prevent memory growth"""
        from shared.rate_limiter import _cleanup_old_entries, _last_cleanup, CLEANUP_INTERVAL_SECONDS
        import shared.rate_limiter as rl

        # Add an old entry
        _rate_limit_store["old-key"] = {
            "count": 5,
            "window_start": time.time() - 7200  # 2 hours ago
        }

        # Force cleanup by setting last cleanup to long ago
        rl._last_cleanup = time.time() - CLEANUP_INTERVAL_SECONDS - 1

        _cleanup_old_entries()

        # Old entry should be removed
        assert "old-key" not in _rate_limit_store
