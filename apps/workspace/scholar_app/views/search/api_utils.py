#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-hub/apps/scholar_app/views/search/api_utils.py
# Shared utilities for search API endpoints
# ----------------------------------------
from __future__ import annotations

import hashlib
import os

__FILE__ = "./apps/scholar_app/views/search/api_utils.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------
from django.core.cache import cache
from django.http import JsonResponse

from scitex import logging

logger = logging.getLogger(__name__)


# Rate limit info for each source
RATE_LIMIT_INFO = {
    "pubmed": "PubMed API: 3 requests/sec without API key",
    "arxiv": "arXiv API: 1 request/3 sec recommended",
    "semantic_scholar": "Semantic Scholar: 10 results max, strict rate limits",
    "crossref": "CrossRef API: Polite pool (faster with contact email)",
    "crossref_local": "Local database: No rate limits",
    "openalex": "OpenAlex API: 10 requests/sec max",
    "pmc": "PMC API: Similar to PubMed limits",
    "doaj": "DOAJ API: Moderate rate limits",
    "biorxiv": "bioRxiv API: Moderate rate limits",
    "plos": "PLOS API: Moderate rate limits",
}


def cached_search(request, source_name, search_func, max_results, cache_ttl=1800):
    """Helper for cached API searches with ignore_cache support."""
    from .config import get_limit_for_source

    query = request.GET.get("q", "").strip()
    ignore_cache = request.GET.get("ignore_cache", "").lower() == "true"

    if not query:
        return JsonResponse({"error": "Query parameter required"}, status=400)

    # Check cache unless ignore_cache is set
    cache_key = f"{source_name}_search_{hashlib.md5(f'{query}_{max_results}'.encode()).hexdigest()}"
    if not ignore_cache:
        cached = cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return JsonResponse(cached)

    try:
        results = search_func(query, max_results=max_results)
        result_count = len(results)
        configured_max = get_limit_for_source(
            source_name, request.user if request.user.is_authenticated else None
        )

        # Build result guidance
        result_guidance = _build_result_guidance(
            source_name=source_name,
            received=result_count,
            requested=max_results,
            configured_max=configured_max,
        )

        response_data = {
            "status": "success",
            "source": source_name,
            "query": query,
            "count": result_count,
            "results": results,
            "result_guidance": result_guidance,
        }
        # Cache the results
        cache.set(cache_key, response_data, cache_ttl)
        return JsonResponse(response_data)
    except Exception as e:
        logger.error(f"{source_name} API search failed: {e}")
        return JsonResponse(
            {"status": "error", "source": source_name, "error": str(e)}, status=500
        )


def _build_result_guidance(
    source_name, received, requested, configured_max, error=None
):
    """Build result guidance dict explaining why results are limited."""
    # Build reason explanation
    if error:
        reason = f"Error: {error}"
    elif received == 0:
        reason = "No matching results found"
    elif received < requested:
        reasons = []
        if source_name in RATE_LIMIT_INFO:
            reasons.append(RATE_LIMIT_INFO[source_name])
        if received < 5:
            reasons.append("Very few matches - try broader terms")
        elif received < requested // 2:
            reasons.append("API returned fewer than requested")
        reason = " | ".join(reasons) if reasons else f"Returned {received}/{requested}"
    else:
        reason = f"Received all {received} requested results"

    return {
        "source": source_name,
        "requested": requested,
        "received": received,
        "configured_max": configured_max,
        "reason": reason,
        "rate_limit_info": RATE_LIMIT_INFO.get(source_name, "Unknown"),
    }


def explain_result_count(source_name, received, requested, error=None):
    """Explain why a source returned a specific number of results."""
    if error:
        return f"Error occurred: {error}"

    if received == 0:
        return "No matching results found in this source"

    if received < requested:
        reasons = []

        # Source-specific explanations
        if source_name == "crossref":
            reasons.append("CrossRef API has strict rate limits")
            if received < 10:
                reasons.append(
                    "Limited results may indicate rate limiting or narrow query match"
                )
        elif source_name == "crossref_local":
            reasons.append("Local database query - no rate limits")
            if received == 0:
                reasons.append(
                    "Database may not be populated or query doesn't match local data"
                )
        elif source_name == "semantic":
            reasons.append(
                "Semantic Scholar has aggressive rate limiting (10 results max)"
            )
        elif source_name == "pubmed":
            if received < requested / 2:
                reasons.append(
                    "PubMed API may be rate limiting or query is very specific"
                )
        elif source_name == "openalex":
            if received == 50:
                reasons.append("Default limit reached (50 results)")

        # Generic explanations
        if received < 5:
            reasons.append("Very few matches - try broader search terms")
        elif received < requested / 2:
            reasons.append("API returned fewer results than requested")
        else:
            reasons.append(f"Source returned {received}/{requested} requested results")

        return " | ".join(reasons)

    return f"Received all {received} requested results"


def build_unified_result_guidance(
    request, results, source_data, max_results, engine="django"
):
    """Build result guidance for unified search results."""
    from ...middleware.rate_limit import rate_limit_status
    from .config import get_limit_for_source

    # Calculate totals based on engine
    if engine == "scitex":
        total_before_dedup = sum(
            meta.get("result_count", 0) for meta in source_data.values()
        )
    else:
        total_before_dedup = sum(
            stats.get("count", 0) for stats in source_data.values()
        )

    deduplication_count = total_before_dedup - len(results)

    # Build per-source limits
    per_source_limits = {}
    for source, data in source_data.items():
        if engine == "scitex":
            received = data.get("result_count", 0)
            error = data.get("error")
        else:
            received = data.get("count", 0)
            error = data.get("error")

        per_source_limits[source] = {
            "requested": max_results,
            "received": received,
            "configured_max": get_limit_for_source(source, request.user),
            "reason": explain_result_count(source, received, max_results, error),
        }

    return {
        "total_fetched": total_before_dedup,
        "total_after_dedup": len(results),
        "deduplication": {
            "removed": deduplication_count,
            "explanation": "Duplicate papers (same DOI/title) removed across sources",
        },
        "per_source_limits": per_source_limits,
        "rate_limiting": {
            "applied": True,
            "details": rate_limit_status(request, "api_search_unified"),
            "explanation": "Rate limits protect external APIs and ensure service stability",
        },
    }
