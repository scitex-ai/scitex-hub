#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/search/api_unified.py
# Unified search API endpoint with command syntax support
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/scholar_app/views/search/api_unified.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from scitex import logging

from ...api_auth import api_key_optional
from ...integrations import scitex_scholar as scitex_integration
from ...middleware.rate_limit import rate_limit, rate_limit_status
from .api_filters import (
    extract_django_filters,
    extract_scitex_filters,
    format_results_compact,
    get_syntax_help_brief,
)
from .api_utils import build_unified_result_guidance
from .engines import (
    search_arxiv,
    search_biorxiv,
    search_doaj,
    search_plos,
    search_pubmed,
    search_pubmed_central,
    search_semantic_scholar,
)
from .search_helpers import apply_advanced_filters, parse_query_operators

logger = logging.getLogger(__name__)


@api_key_optional
@rate_limit("api_search_unified")
@require_http_methods(["GET"])
def api_search_unified(request):
    """
    Unified RESTful API for academic literature search.

    Supports shell-style command syntax for filtering.
    See api_search_syntax_help for full documentation.
    """
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse(
            {
                "status": "error",
                "error": "Query parameter 'q' is required",
                "syntax_help": get_syntax_help_brief(),
            },
            status=400,
        )

    try:
        max_results = min(int(request.GET.get("max_results", 20)), 100)
    except ValueError:
        max_results = 20
    response_format = request.GET.get("format", "full").lower()
    use_scitex = request.GET.get("engine", "auto").lower() != "django"

    # Try scitex.scholar engine first
    if use_scitex and scitex_integration.is_available():
        result = _search_with_scitex(request, query, max_results, response_format)
        if result:
            return result

    return _search_with_django(request, query, max_results, response_format)


def _search_with_scitex(request, query, max_results, response_format):
    """Execute search using scitex.scholar engine."""
    try:
        scitex_results = scitex_integration.search_sync(
            query=query,
            mode="parallel",
            max_results=max_results,
            email=(
                getattr(request.user, "email", None)
                if request.user.is_authenticated
                else None
            ),
        )

        formatted_results = scitex_integration.convert_scitex_results_to_django(
            scitex_results
        )
        parsed = scitex_integration.parse_query_scitex(query)
        source_metadata = scitex_results.get("metadata", {}).get("sources", {})

        return JsonResponse(
            {
                "status": "success",
                "engine": "scitex.scholar",
                "query": {
                    "original": query,
                    "parsed": parsed.get("keyword_query", query),
                    "filters": extract_scitex_filters(parsed),
                },
                "sources": source_metadata,
                "total_count": len(formatted_results),
                "results": _format_results(formatted_results, response_format),
                "stats": scitex_results.get("stats", {}),
                "rate_limit": rate_limit_status(request, "api_search_unified"),
                "result_guidance": build_unified_result_guidance(
                    request, formatted_results, source_metadata, max_results, "scitex"
                ),
            }
        )
    except Exception as e:
        logger.warning(f"scitex.scholar search failed, falling back to Django: {e}")
        return None


def _search_with_django(request, query, max_results, response_format):
    """Execute search using Django-only implementation."""
    parsed = parse_query_operators(query)
    clean_query = parsed.get("query", query)

    sources_to_search = _get_sources_to_search(request)
    all_results, source_stats, errors = _execute_parallel_search(
        sources_to_search, clean_query, max_results
    )

    filtered_results = apply_advanced_filters(all_results, None, parsed)
    filtered_results.sort(
        key=lambda x: (-(x.get("citations") or 0), -(int(x.get("year") or 0)))
    )

    return JsonResponse(
        {
            "status": "success",
            "engine": "django",
            "query": {
                "original": query,
                "parsed": clean_query,
                "filters": extract_django_filters(parsed),
            },
            "sources": source_stats,
            "total_count": len(filtered_results),
            "results": _format_results(filtered_results, response_format),
            "errors": errors if errors else None,
            "rate_limit": rate_limit_status(request, "api_search_unified"),
            "result_guidance": build_unified_result_guidance(
                request, filtered_results, source_stats, max_results, "django"
            ),
        }
    )


def _get_sources_to_search(request):
    """Determine which sources to search based on request."""
    sources_param = request.GET.get("sources", "").strip()
    available_sources = {
        "pubmed": search_pubmed,
        "arxiv": search_arxiv,
        "semantic": search_semantic_scholar,
        "pmc": search_pubmed_central,
        "doaj": search_doaj,
        "biorxiv": search_biorxiv,
        "plos": search_plos,
    }

    if sources_param:
        requested_sources = [s.strip().lower() for s in sources_param.split(",")]
        return {k: v for k, v in available_sources.items() if k in requested_sources}

    # Default to main sources for performance
    return {
        "pubmed": search_pubmed,
        "arxiv": search_arxiv,
        "semantic": search_semantic_scholar,
    }


def _execute_parallel_search(sources, query, max_results):
    """Execute search across multiple sources in parallel."""
    all_results = []
    source_stats = {}
    errors = []

    def search_source(name, search_func):
        try:
            results = search_func(query, max_results=max_results)
            return name, results, None
        except Exception as e:
            return name, [], str(e)

    with ThreadPoolExecutor(max_workers=len(sources)) as executor:
        futures = {
            executor.submit(search_source, name, func): name
            for name, func in sources.items()
        }

        for future in as_completed(futures):
            source_name, results, error = future.result()
            if error:
                errors.append({"source": source_name, "error": error})
                source_stats[source_name] = {"count": 0, "status": "error"}
            else:
                source_stats[source_name] = {"count": len(results), "status": "success"}
                all_results.extend(results)

    return all_results, source_stats, errors


def _format_results(results, response_format):
    """Format results based on requested format."""
    if response_format == "compact":
        return format_results_compact(results)
    return results
