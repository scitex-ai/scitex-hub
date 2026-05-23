#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-hub/apps/scholar_app/middleware/rate_limit.py
"""
Rate limiting utilities for Scholar API endpoints.

Provides sliding window rate limiting with Redis or in-memory fallback.
"""

import time
import logging
from functools import wraps
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# Default rate limits by tier
RATE_LIMITS = {
    "anonymous": {"requests": 30, "window": 60},  # 30/minute
    "authenticated": {"requests": 100, "window": 60},  # 100/minute
    "api_key_basic": {"requests": 500, "window": 60},  # 500/minute
    "api_key_premium": {"requests": 2000, "window": 60},  # 2000/minute
}

# Endpoint-specific limits (overrides tier limits)
ENDPOINT_LIMITS = {
    "api_search_unified": {"requests": 60, "window": 60},  # 60/minute
    "api_search_crossref": {"requests": 30, "window": 60},  # CrossRef has strict limits
    "api_search_semantic": {"requests": 20, "window": 60},  # Semantic Scholar limits
}


def get_client_ip(request):
    """Extract client IP from request, handling proxies."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def get_rate_limit_key(request, endpoint_name=None):
    """Generate a unique cache key for rate limiting."""
    # Priority: API key > authenticated user > IP
    if hasattr(request, "api_key") and request.api_key:
        identifier = f"apikey:{request.api_key.id}"
    elif request.user.is_authenticated:
        identifier = f"user:{request.user.id}"
    else:
        identifier = f"ip:{get_client_ip(request)}"

    prefix = f"ratelimit:{endpoint_name}:" if endpoint_name else "ratelimit:global:"
    return f"{prefix}{identifier}"


def get_user_tier(request):
    """Determine the user's rate limit tier."""
    if hasattr(request, "api_key") and request.api_key:
        # Check API key scopes for premium
        if "premium" in request.api_key.scopes or "*" in request.api_key.scopes:
            return "api_key_premium"
        return "api_key_basic"
    elif request.user.is_authenticated:
        return "authenticated"
    return "anonymous"


def check_rate_limit(request, endpoint_name=None):
    """
    Check if the request is within rate limits.

    Returns:
        tuple: (is_allowed, remaining, reset_time, limit)
    """
    tier = get_user_tier(request)
    cache_key = get_rate_limit_key(request, endpoint_name)

    # Get limit configuration
    if endpoint_name and endpoint_name in ENDPOINT_LIMITS:
        config = ENDPOINT_LIMITS[endpoint_name]
    else:
        config = RATE_LIMITS.get(tier, RATE_LIMITS["anonymous"])

    limit = config["requests"]
    window = config["window"]

    # Get current window data
    now = time.time()
    window_start = now - window

    # Get or create the sliding window data
    window_data = cache.get(cache_key, [])

    # Filter to only requests within the current window
    window_data = [ts for ts in window_data if ts > window_start]

    # Check if within limit
    current_count = len(window_data)
    is_allowed = current_count < limit

    if is_allowed:
        # Add current request timestamp
        window_data.append(now)
        cache.set(cache_key, window_data, timeout=window + 10)

    # Calculate remaining and reset time
    remaining = max(0, limit - len(window_data))
    reset_time = int(window_start + window)

    return is_allowed, remaining, reset_time, limit


def rate_limit(endpoint_name=None):
    """
    Decorator to apply rate limiting to a view.

    Usage:
        @rate_limit("api_search_unified")
        def my_view(request):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            is_allowed, remaining, reset_time, limit = check_rate_limit(
                request, endpoint_name
            )

            if not is_allowed:
                response = JsonResponse(
                    {
                        "success": False,
                        "error": "Rate limit exceeded",
                        "detail": f"Too many requests. Limit: {limit}/minute",
                        "retry_after": reset_time - int(time.time()),
                    },
                    status=429,
                )
                response["X-RateLimit-Limit"] = str(limit)
                response["X-RateLimit-Remaining"] = "0"
                response["X-RateLimit-Reset"] = str(reset_time)
                response["Retry-After"] = str(reset_time - int(time.time()))
                return response

            # Execute the view
            response = view_func(request, *args, **kwargs)

            # Add rate limit headers to successful responses
            if hasattr(response, "__setitem__"):
                response["X-RateLimit-Limit"] = str(limit)
                response["X-RateLimit-Remaining"] = str(remaining)
                response["X-RateLimit-Reset"] = str(reset_time)

            return response

        return wrapper

    return decorator


def rate_limit_status(request, endpoint_name=None):
    """Get current rate limit status for a request."""
    is_allowed, remaining, reset_time, limit = check_rate_limit(request, endpoint_name)
    return {
        "limit": limit,
        "remaining": remaining,
        "reset": reset_time,
        "tier": get_user_tier(request),
    }


# EOF
