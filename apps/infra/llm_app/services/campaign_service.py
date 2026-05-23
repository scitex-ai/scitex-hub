#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Campaign Chat Service

Provides AI chat access using a shared Anthropic API key (Haiku model)
with per-IP daily rate limiting. Enables researchers to try the AI chat
without configuring their own API key.
"""

from __future__ import annotations

import logging
from datetime import date

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CAMPAIGN_CACHE_PREFIX = "campaign_chat"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_DAILY_LIMIT = 10
MAX_TOKENS = 2048


def _get_client_ip(request) -> str:
    """Extract client IP, handling proxies."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def is_campaign_enabled() -> bool:
    """Check if campaign chat mode is configured."""
    return bool(getattr(settings, "SCITEX_HUB_CAMPAIGN_ANTHROPIC_API_KEY", ""))


def get_campaign_config() -> dict:
    """Return campaign configuration from settings."""
    return {
        "api_key": settings.SCITEX_HUB_CAMPAIGN_ANTHROPIC_API_KEY,
        "model": getattr(settings, "SCITEX_HUB_CAMPAIGN_MODEL", DEFAULT_MODEL),
        "daily_limit": int(
            getattr(settings, "SCITEX_HUB_CAMPAIGN_DAILY_LIMIT", DEFAULT_DAILY_LIMIT)
        ),
    }


def check_campaign_rate_limit(request) -> tuple[bool, int, str | None]:
    """Check if request is within campaign rate limit.

    Returns:
        (allowed, remaining, error_message)
    """
    ip = _get_client_ip(request)
    config = get_campaign_config()
    cache_key = f"{CAMPAIGN_CACHE_PREFIX}:{ip}:{date.today()}"
    count = cache.get(cache_key, 0)

    if count >= config["daily_limit"]:
        return (
            False,
            0,
            f"Daily campaign limit reached ({config['daily_limit']}/day). "
            "Configure your own API key for unlimited access.",
        )
    return True, config["daily_limit"] - count - 1, None


def increment_campaign_usage(request) -> None:
    """Increment the daily usage counter for this IP."""
    ip = _get_client_ip(request)
    cache_key = f"{CAMPAIGN_CACHE_PREFIX}:{ip}:{date.today()}"
    count = cache.get(cache_key, 0)
    cache.set(cache_key, count + 1, timeout=86400)


async def campaign_complete_streaming(messages: list[dict]):
    """Stream completion from Anthropic Haiku using the campaign key."""
    import litellm

    config = get_campaign_config()
    model_string = f"anthropic/{config['model']}"

    logger.info("Campaign chat: model=%s", model_string)

    return await litellm.acompletion(
        model=model_string,
        api_key=config["api_key"],
        messages=messages,
        stream=True,
        max_tokens=MAX_TOKENS,
    )


# EOF
