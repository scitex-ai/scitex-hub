#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/scholar_app/api/public_search_utils.py
"""Utilities for public search API - rate limiting, auth, and search helpers."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from typing import Callable

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger(__name__)

# Rate limit settings
RATE_LIMIT_ANONYMOUS = 10  # requests per minute
RATE_LIMIT_CAMPAIGN = 50  # requests per minute (shared key)
RATE_LIMIT_USER = 100  # requests per minute (per-user key)
RATE_LIMIT_WINDOW = 60  # seconds


def get_client_ip(request: HttpRequest) -> str:
    """Get client IP address from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def get_api_key(request: HttpRequest) -> str | None:
    """Extract API key from request (header or query param)."""
    api_key = request.META.get("HTTP_X_SCITEX_API_KEY")
    if api_key:
        return api_key
    return request.GET.get("api_key")


def validate_api_key(api_key: str) -> tuple[bool, str]:
    """Validate API key against database or environment."""
    from django.conf import settings

    campaign_key = getattr(settings, "SCITEX_CLOUD_CAMPAIGN_API_KEY", None)
    if campaign_key and api_key == campaign_key:
        return True, "campaign"

    try:
        from apps.accounts_app.models import APIKey

        key_obj = APIKey.objects.filter(
            key_hash=APIKey.hash_key(api_key),
            is_active=True,
        ).first()

        if key_obj:
            from django.utils import timezone

            key_obj.last_used_at = timezone.now()
            key_obj.save(update_fields=["last_used_at"])
            return True, "user"
    except Exception as e:
        logger.warning(f"API key validation error: {e}")

    return False, "invalid"


def rate_limit(func: Callable) -> Callable:
    """Rate limiting decorator for API views."""

    @wraps(func)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        api_key = get_api_key(request)
        key_type = "anonymous"

        if api_key:
            is_valid, key_type = validate_api_key(api_key)
            if not is_valid:
                return JsonResponse({"error": "Invalid API key"}, status=401)

        if key_type == "user":
            limit = RATE_LIMIT_USER
            cache_key = f"ratelimit:user:{api_key[:16]}"
        elif key_type == "campaign":
            limit = RATE_LIMIT_CAMPAIGN
            client_ip = get_client_ip(request)
            cache_key = f"ratelimit:campaign:{client_ip}"
        else:
            limit = RATE_LIMIT_ANONYMOUS
            client_ip = get_client_ip(request)
            cache_key = f"ratelimit:anon:{client_ip}"

        current = cache.get(cache_key, 0)

        if current >= limit:
            return JsonResponse(
                {
                    "error": "Rate limit exceeded",
                    "limit": limit,
                    "window": f"{RATE_LIMIT_WINDOW} seconds",
                    "key_type": key_type,
                    "hint": "Register for an API key for higher limits"
                    if key_type != "user"
                    else None,
                },
                status=429,
            )

        cache.set(cache_key, current + 1, RATE_LIMIT_WINDOW)

        response = func(request, *args, **kwargs)
        response["X-RateLimit-Limit"] = str(limit)
        response["X-RateLimit-Remaining"] = str(limit - current - 1)
        response["X-RateLimit-Window"] = str(RATE_LIMIT_WINDOW)
        response["X-RateLimit-KeyType"] = key_type

        return response

    return wrapper


def search_external_sources(
    query: str, sources: list[str], limit: int
) -> tuple[list[dict], dict]:
    """Search external academic sources in parallel."""
    import requests

    from ..views.search.api_crossref import _parse_crossref_results
    from ..views.search.api_openalex import _parse_openalex_results
    from ..views.search.engines import (
        search_arxiv,
        search_pubmed,
        search_semantic_scholar,
    )

    available_sources = {
        "pubmed": search_pubmed,
        "arxiv": search_arxiv,
        "semantic": search_semantic_scholar,
    }

    results = []
    source_stats = {}

    def search_source(name: str, search_func: Callable) -> tuple[str, list, str | None]:
        try:
            source_results = search_func(query, max_results=limit)
            return name, source_results, None
        except Exception as e:
            return name, [], str(e)

    def search_crossref() -> tuple[str, list, str | None]:
        try:
            url = "https://api.crossref.org/works"
            params = {
                "query": query,
                "rows": limit,
                "select": "DOI,title,author,published-print,published-online,"
                "container-title,is-referenced-by-count,abstract",
            }
            headers = {
                "User-Agent": "SciTeX/1.0 (https://scitex.ai; mailto:contact@scitex.ai)"
            }
            response = requests.get(url, params=params, headers=headers, timeout=60)
            response.raise_for_status()
            return "crossref", _parse_crossref_results(response.json(), query), None
        except Exception as e:
            return "crossref", [], str(e)

    def search_openalex() -> tuple[str, list, str | None]:
        try:
            url = "https://api.openalex.org/works"
            params = {
                "search": query,
                "per-page": limit,
                "select": "id,doi,title,authorships,publication_year,"
                "primary_location,cited_by_count,abstract_inverted_index,open_access",
            }
            headers = {
                "User-Agent": "SciTeX/1.0 (https://scitex.ai; mailto:contact@scitex.ai)"
            }
            response = requests.get(url, params=params, headers=headers, timeout=60)
            response.raise_for_status()
            return "openalex", _parse_openalex_results(response.json()), None
        except Exception as e:
            return "openalex", [], str(e)

    tasks = []
    for source in sources:
        if source in available_sources:
            tasks.append((source, available_sources[source]))
        elif source == "crossref":
            tasks.append(("crossref", None))
        elif source == "openalex":
            tasks.append(("openalex", None))

    with ThreadPoolExecutor(max_workers=min(len(tasks), 5)) as executor:
        futures = []
        for source_name, search_func in tasks:
            if source_name == "crossref":
                futures.append(executor.submit(search_crossref))
            elif source_name == "openalex":
                futures.append(executor.submit(search_openalex))
            elif search_func:
                futures.append(executor.submit(search_source, source_name, search_func))

        for future in as_completed(futures):
            source_name, source_results, error = future.result()
            if error:
                source_stats[source_name] = {
                    "count": 0,
                    "status": "error",
                    "error": error,
                }
            else:
                source_stats[source_name] = {
                    "count": len(source_results),
                    "status": "success",
                }
                results.extend(source_results)

    return results, source_stats


# EOF
