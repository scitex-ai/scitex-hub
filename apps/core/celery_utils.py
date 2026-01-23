# -*- coding: utf-8 -*-
# Timestamp: 2025-11-25
# Author: ywatanabe
# File: apps/core/celery_utils.py

"""
Celery utilities for per-user rate limiting and fair scheduling.

This module provides decorators and utilities for implementing fair
resource allocation across users in Celery tasks.
"""

import logging
import time
from functools import wraps
from typing import Callable, Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)


class UserRateLimiter:
    """
    Per-user rate limiter using Redis cache.

    Implements token bucket algorithm for fair rate limiting.
    """

    def __init__(
        self,
        key_prefix: str = "rate_limit",
        requests_per_minute: int = 10,
        burst_size: int = 5,
    ):
        """
        Initialize rate limiter.

        Args:
            key_prefix: Cache key prefix for this limiter
            requests_per_minute: Base rate limit
            burst_size: Maximum burst allowed
        """
        self.key_prefix = key_prefix
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.refill_rate = requests_per_minute / 60.0  # tokens per second

    def _get_cache_key(self, user_id: int) -> str:
        """Get cache key for user."""
        return f"{self.key_prefix}:{user_id}"

    def is_allowed(self, user_id: int) -> tuple[bool, dict]:
        """
        Check if request is allowed for user.

        Args:
            user_id: User ID to check

        Returns:
            Tuple of (allowed: bool, info: dict)
        """
        cache_key = self._get_cache_key(user_id)
        now = time.time()

        # Get current bucket state
        bucket = cache.get(cache_key)

        if bucket is None:
            # Initialize new bucket
            bucket = {
                "tokens": self.burst_size,
                "last_update": now,
            }

        # Calculate tokens to add since last update
        time_passed = now - bucket["last_update"]
        tokens_to_add = time_passed * self.refill_rate
        bucket["tokens"] = min(self.burst_size, bucket["tokens"] + tokens_to_add)
        bucket["last_update"] = now

        # Check if request is allowed
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            cache.set(cache_key, bucket, timeout=300)  # 5 min timeout
            return True, {
                "remaining": int(bucket["tokens"]),
                "limit": self.requests_per_minute,
                "reset_in": int((self.burst_size - bucket["tokens"]) / self.refill_rate),
            }
        else:
            cache.set(cache_key, bucket, timeout=300)
            wait_time = (1 - bucket["tokens"]) / self.refill_rate
            return False, {
                "remaining": 0,
                "limit": self.requests_per_minute,
                "retry_after": int(wait_time) + 1,
            }

    def reset(self, user_id: int):
        """Reset rate limit for user."""
        cache_key = self._get_cache_key(user_id)
        cache.delete(cache_key)


def user_rate_limit(
    requests_per_minute: int = 10,
    burst_size: int = 5,
    key_prefix: Optional[str] = None,
):
    """
    Decorator for per-user rate limiting in Celery tasks.

    Usage:
        @shared_task
        @user_rate_limit(requests_per_minute=10, burst_size=5)
        def my_task(user_id, ...):
            ...

    Args:
        requests_per_minute: Maximum requests per minute per user
        burst_size: Maximum burst size
        key_prefix: Cache key prefix (defaults to function name)
    """

    def decorator(func: Callable) -> Callable:
        limiter = UserRateLimiter(
            key_prefix=key_prefix or f"rate:{func.__name__}",
            requests_per_minute=requests_per_minute,
            burst_size=burst_size,
        )

        @wraps(func)
        def wrapper(self_or_user_id, *args, **kwargs):
            # Handle both bound tasks (self, user_id) and unbound (user_id)
            if hasattr(self_or_user_id, "request"):
                # Bound task: first arg is self
                self = self_or_user_id
                user_id = args[0] if args else kwargs.get("user_id")
                remaining_args = args[1:]
            else:
                # Unbound: first arg is user_id
                self = None
                user_id = self_or_user_id
                remaining_args = args

            if user_id is None:
                logger.warning(f"No user_id provided to {func.__name__}")
                if self:
                    return func(self, user_id, *remaining_args, **kwargs)
                return func(user_id, *remaining_args, **kwargs)

            # Check rate limit
            allowed, info = limiter.is_allowed(user_id)

            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for user {user_id} on {func.__name__}"
                )
                return {
                    "success": False,
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Try again in {info['retry_after']} seconds.",
                    "retry_after": info["retry_after"],
                }

            # Execute task
            if self:
                result = func(self, user_id, *remaining_args, **kwargs)
            else:
                result = func(user_id, *remaining_args, **kwargs)

            # Add rate limit info to result if it's a dict
            if isinstance(result, dict):
                result["rate_limit"] = info

            return result

        return wrapper

    return decorator


# Pre-configured limiters for common use cases
AI_RATE_LIMITER = UserRateLimiter(
    key_prefix="rate:ai",
    requests_per_minute=10,
    burst_size=5,
)

SEARCH_RATE_LIMITER = UserRateLimiter(
    key_prefix="rate:search",
    requests_per_minute=30,
    burst_size=10,
)

PDF_RATE_LIMITER = UserRateLimiter(
    key_prefix="rate:pdf",
    requests_per_minute=20,
    burst_size=5,
)


def get_user_quota_status(user_id: int) -> dict:
    """
    Get current quota status for a user across all limiters.

    Args:
        user_id: User ID to check

    Returns:
        Dict with quota status for each service
    """
    return {
        "ai": AI_RATE_LIMITER.is_allowed(user_id)[1],
        "search": SEARCH_RATE_LIMITER.is_allowed(user_id)[1],
        "pdf": PDF_RATE_LIMITER.is_allowed(user_id)[1],
    }


# EOF
