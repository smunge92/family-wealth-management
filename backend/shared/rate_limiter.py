"""
Rate limiting for API endpoints.

Supports two storage backends:
1. In-memory storage (default) - for single instance deployments
2. Redis/Azure Cache - for multi-instance deployments (set REDIS_URL env var)

To enable Redis:
    Set REDIS_URL environment variable (e.g., "redis://localhost:6379" or Azure Cache connection string)
    Install redis package: pip install redis
"""

import os
import time
import logging
import json
from typing import Dict, Optional, Callable
from functools import wraps
import azure.functions as func
from shared.auth import get_cors_headers, get_user_from_request

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL")
_redis_client = None


_redis_warning_logged = False


def _get_redis_client():
    """Get Redis client (lazy initialization)"""
    global _redis_client, _redis_warning_logged
    if _redis_client is None and REDIS_URL:
        try:
            import redis
            _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            logger.info("Redis rate limiting enabled")
        except ImportError:
            logger.warning("redis package not installed - falling back to in-memory rate limiting")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e} - falling back to in-memory rate limiting")

    # Warn once if using in-memory rate limiting in production
    if _redis_client is None and not _redis_warning_logged:
        is_production = os.getenv("REQUIRE_AUTH", "true").lower() == "true"
        if is_production:
            logger.warning(
                "Rate limiting is using in-memory storage with REQUIRE_AUTH=true. "
                "In-memory rate limits are not shared across multiple instances. "
                "Set REDIS_URL for distributed rate limiting in production."
            )
        _redis_warning_logged = True

    return _redis_client


# In-memory rate limit storage (fallback)
# Structure: { "user_id:endpoint": { "count": int, "window_start": float } }
_rate_limit_store: Dict[str, Dict] = {}

# Clean up old entries periodically
_last_cleanup = time.time()
CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, limit: int, window_seconds: int, retry_after: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded: {limit} requests per {window_seconds} seconds")


def _cleanup_old_entries():
    """Remove expired rate limit entries to prevent memory growth (in-memory only)."""
    global _last_cleanup
    current_time = time.time()

    if current_time - _last_cleanup < CLEANUP_INTERVAL_SECONDS:
        return

    _last_cleanup = current_time
    expired_keys = []

    for key, data in _rate_limit_store.items():
        # Remove entries older than 1 hour
        if current_time - data.get("window_start", 0) > 3600:
            expired_keys.append(key)

    for key in expired_keys:
        del _rate_limit_store[key]

    if expired_keys:
        logger.debug(f"Cleaned up {len(expired_keys)} expired rate limit entries")


def check_rate_limit(
    user_id: str,
    endpoint: str,
    limit: int,
    window_seconds: int
) -> tuple[bool, int]:
    """
    Check if a request is within rate limits.

    Uses Redis if available, otherwise falls back to in-memory storage.

    Args:
        user_id: The user making the request
        endpoint: The endpoint being accessed
        limit: Maximum number of requests allowed
        window_seconds: Time window in seconds

    Returns:
        Tuple of (is_allowed, retry_after_seconds)
    """
    redis_client = _get_redis_client()

    if redis_client:
        return _check_rate_limit_redis(redis_client, user_id, endpoint, limit, window_seconds)
    else:
        return _check_rate_limit_memory(user_id, endpoint, limit, window_seconds)


def _check_rate_limit_redis(
    redis_client,
    user_id: str,
    endpoint: str,
    limit: int,
    window_seconds: int
) -> tuple[bool, int]:
    """Check rate limit using Redis (distributed, multi-instance safe)"""
    key = f"ratelimit:{user_id}:{endpoint}"

    try:
        # Use Redis INCR with EXPIRE for atomic sliding window
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        results = pipe.execute()

        current_count = results[0]
        ttl = results[1]

        # If this is a new key (ttl is -1), set the expiration
        if ttl == -1:
            redis_client.expire(key, window_seconds)
            ttl = window_seconds

        if current_count > limit:
            retry_after = max(1, ttl)
            return False, retry_after

        return True, 0

    except Exception as e:
        logger.warning(f"Redis rate limit check failed: {e} - falling back to allow")
        return True, 0  # Fail open to avoid blocking legitimate requests


def _check_rate_limit_memory(
    user_id: str,
    endpoint: str,
    limit: int,
    window_seconds: int
) -> tuple[bool, int]:
    """Check rate limit using in-memory storage (single instance only)"""
    _cleanup_old_entries()

    current_time = time.time()
    key = f"{user_id}:{endpoint}"

    if key not in _rate_limit_store:
        _rate_limit_store[key] = {
            "count": 1,
            "window_start": current_time
        }
        return True, 0

    data = _rate_limit_store[key]
    window_start = data["window_start"]

    # Check if we're in a new window
    if current_time - window_start >= window_seconds:
        _rate_limit_store[key] = {
            "count": 1,
            "window_start": current_time
        }
        return True, 0

    # Check if limit exceeded
    if data["count"] >= limit:
        retry_after = int(window_seconds - (current_time - window_start))
        return False, max(1, retry_after)

    # Increment count
    data["count"] += 1
    return True, 0


def rate_limit(
    limit: int = 60,
    window_seconds: int = 60,
    endpoint_name: Optional[str] = None,
    key_func: Optional[Callable] = None
):
    """
    Decorator to apply rate limiting to an Azure Function.

    Args:
        limit: Maximum number of requests allowed in the window
        window_seconds: Time window in seconds
        endpoint_name: Optional custom endpoint name (defaults to function name)
        key_func: Optional function to extract the rate limit key from request
                  (defaults to user_id from auth)

    Usage:
        @bp.route(route="api/endpoint", methods=["GET"])
        @require_auth
        @rate_limit(limit=10, window_seconds=60)
        async def my_endpoint(req: func.HttpRequest) -> func.HttpResponse:
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        async def async_wrapper(req: func.HttpRequest, *args, **kwargs) -> func.HttpResponse:
            headers = get_cors_headers()

            # Get the rate limit key - SECURITY: Only use authenticated user ID
            # Do NOT use X-Forwarded-For or other spoofable headers
            if key_func:
                rate_key = key_func(req)
            else:
                user_info = get_user_from_request(req)
                if user_info and user_info.get("user_id"):
                    rate_key = user_info.get("user_id")
                else:
                    # For unauthenticated requests, use a global key with stricter limits
                    # This prevents header spoofing attacks but may be too restrictive
                    # in high-traffic scenarios - consider implementing IP-based limiting
                    # at the infrastructure level (Azure Front Door, WAF) instead
                    rate_key = "_anonymous_global_"

            # Get endpoint name
            ep_name = endpoint_name or f.__name__

            # Check rate limit
            is_allowed, retry_after = check_rate_limit(rate_key, ep_name, limit, window_seconds)

            if not is_allowed:
                logger.warning(f"Rate limit exceeded for {rate_key} on {ep_name}")
                headers["Retry-After"] = str(retry_after)
                headers["X-RateLimit-Limit"] = str(limit)
                headers["X-RateLimit-Remaining"] = "0"
                headers["X-RateLimit-Reset"] = str(int(time.time()) + retry_after)

                return func.HttpResponse(
                    json.dumps({
                        "error": "Rate limit exceeded",
                        "retry_after": retry_after
                    }),
                    status_code=429,
                    mimetype="application/json",
                    headers=headers
                )

            # Add rate limit headers to response
            response = await f(req, *args, **kwargs)

            # Note: We can't easily add headers to the response after the fact
            # in Azure Functions, so the rate limit headers are only added on 429

            return response

        @wraps(f)
        def sync_wrapper(req: func.HttpRequest, *args, **kwargs) -> func.HttpResponse:
            headers = get_cors_headers()

            # Get the rate limit key - SECURITY: Only use authenticated user ID
            # Do NOT use X-Forwarded-For or other spoofable headers
            if key_func:
                rate_key = key_func(req)
            else:
                user_info = get_user_from_request(req)
                if user_info and user_info.get("user_id"):
                    rate_key = user_info.get("user_id")
                else:
                    # For unauthenticated requests, use a global key with stricter limits
                    rate_key = "_anonymous_global_"

            # Get endpoint name
            ep_name = endpoint_name or f.__name__

            # Check rate limit
            is_allowed, retry_after = check_rate_limit(rate_key, ep_name, limit, window_seconds)

            if not is_allowed:
                logger.warning(f"Rate limit exceeded for {rate_key} on {ep_name}")
                headers["Retry-After"] = str(retry_after)
                headers["X-RateLimit-Limit"] = str(limit)
                headers["X-RateLimit-Remaining"] = "0"
                headers["X-RateLimit-Reset"] = str(int(time.time()) + retry_after)

                return func.HttpResponse(
                    json.dumps({
                        "error": "Rate limit exceeded",
                        "retry_after": retry_after
                    }),
                    status_code=429,
                    mimetype="application/json",
                    headers=headers
                )

            return f(req, *args, **kwargs)

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(f):
            return async_wrapper
        return sync_wrapper

    return decorator


# Pre-configured rate limiters for common use cases
def rate_limit_strict(f: Callable) -> Callable:
    """Strict rate limit: 10 requests per minute."""
    return rate_limit(limit=10, window_seconds=60)(f)


def rate_limit_standard(f: Callable) -> Callable:
    """Standard rate limit: 60 requests per minute."""
    return rate_limit(limit=60, window_seconds=60)(f)


def rate_limit_relaxed(f: Callable) -> Callable:
    """Relaxed rate limit: 120 requests per minute."""
    return rate_limit(limit=120, window_seconds=60)(f)


def rate_limit_link_token(f: Callable) -> Callable:
    """Rate limit for Plaid link token: 5 per minute."""
    return rate_limit(limit=5, window_seconds=60, endpoint_name="link_token")(f)


def rate_limit_sync(f: Callable) -> Callable:
    """Rate limit for transaction sync: 2 per minute per user."""
    return rate_limit(limit=2, window_seconds=60, endpoint_name="sync")(f)
