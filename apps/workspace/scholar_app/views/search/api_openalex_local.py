#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2026-02-04
# File: apps/scholar_app/views/search/api_openalex_local.py
"""OpenAlex Local (SciTeX) database search endpoint.

Django is a thin wrapper - all logic delegated to openalex-local package.
"""

from __future__ import annotations

import hashlib
import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .api_utils import _build_result_guidance

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def api_search_openalex_local(request):
    """API endpoint for OpenAlex Local (SciTeX) database search.

    Thin wrapper around openalex-local package.
    All search logic delegated to the package.
    """
    from .config import NO_LIMIT, get_limit_for_source

    query = request.GET.get("q", "").strip()
    ignore_cache = request.GET.get("ignore_cache", "").lower() == "true"

    if not query:
        return JsonResponse({"error": "Query parameter required"}, status=400)

    # Get configured limit from backend
    user = request.user if request.user.is_authenticated else None
    configured_limit = get_limit_for_source("openalex_local", user, resolve=True)
    raw_configured = get_limit_for_source("openalex_local", user, resolve=False)
    is_unlimited = raw_configured == NO_LIMIT

    # Respect frontend max_results if provided
    requested = int(request.GET.get("max_results", configured_limit))
    max_results = min(requested, configured_limit)

    # Check cache
    cache_key = (
        f"openalex_local_{hashlib.md5(f'{query}_{max_results}'.encode()).hexdigest()}"
    )
    if not ignore_cache:
        cached = cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return JsonResponse(cached)

    try:
        from scitex.scholar.local_dbs import openalex_scitex

        # Delegate to openalex-local
        search_result = openalex_scitex.search(query, limit=max_results)

        # Use package's to_dict() - Django just adds source identifier
        results = []
        for work in search_result:
            if not work.title:
                continue
            data = work.to_dict()
            # Add Django-specific fields for frontend compatibility
            data["source"] = "openalex_local"
            data["externalUrl"] = (
                f"https://doi.org/{data['doi']}" if data.get("doi") else ""
            )
            data["citations"] = data.pop("cited_by_count", 0) or 0
            data["journal"] = data.pop("source", "") or ""
            data["pdf_url"] = data.get("oa_url") or ""
            # Format authors for display
            authors = data.get("authors") or []
            data["authors"] = ", ".join(authors[:5]) + (
                "..." if len(authors) > 5 else ""
            )
            results.append(data)

        result_count = len(results)

        # Build limit_info chain
        limit_info_chain = []
        if hasattr(search_result, "limit_info") and search_result.limit_info:
            li = search_result.limit_info
            limit_info_chain.append(
                {
                    "stage": li.stage,
                    "requested": li.requested,
                    "returned": li.returned,
                    "total_available": li.total_available,
                    "capped": li.capped,
                    "capped_reason": li.capped_reason,
                }
            )

        # Django layer info - always provide limit reason
        django_capped = requested > configured_limit
        total_available = getattr(search_result, "total", result_count)
        limit_reason = (
            f"scitex-cloud: Capped from {requested} to {configured_limit}"
            if django_capped
            else f"scitex-cloud: Returned {result_count} of {total_available} available (limit={configured_limit})"
        )
        limit_info_chain.append(
            {
                "stage": "scitex-cloud",
                "requested": requested,
                "returned": result_count,
                "total_available": total_available,
                "configured_limit": "∞" if is_unlimited else configured_limit,
                "is_unlimited": is_unlimited,
                "capped": django_capped,
                "capped_reason": limit_reason if django_capped else None,
                "limit_reason": limit_reason,  # Always present
            }
        )

        response_data = {
            "status": "success",
            "source": "openalex_local",
            "query": query,
            "count": result_count,
            "total_available": getattr(search_result, "total", result_count),
            "results": results,
            "limit_info_chain": limit_info_chain,
            "result_guidance": _build_result_guidance(
                source_name="openalex_local",
                received=result_count,
                requested=max_results,
                configured_max=configured_limit,
            ),
        }
        cache.set(cache_key, response_data, 1800)
        return JsonResponse(response_data)

    except ImportError as e:
        logger.error(f"openalex-local not installed: {e}")
        return JsonResponse(
            {
                "status": "error",
                "source": "openalex_local",
                "error": "Package not installed",
                "detail": str(e),
            },
            status=503,
        )
    except FileNotFoundError as e:
        logger.error(f"OpenAlex database not found: {e}")
        return JsonResponse(
            {
                "status": "error",
                "source": "openalex_local",
                "error": "Database not found",
                "detail": str(e),
            },
            status=503,
        )
    except ConnectionError as e:
        logger.warning(f"OpenAlex Local server unreachable: {e}")
        return JsonResponse(
            {
                "status": "error",
                "source": "openalex_local",
                "error": "Server unreachable",
                "detail": str(e),
            },
            status=503,
        )
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "busy" in error_msg.lower():
            return JsonResponse(
                {
                    "status": "unavailable",
                    "source": "openalex_local",
                    "error": "Server busy",
                    "detail": error_msg,
                },
                status=503,
            )
        logger.exception(f"OpenAlex Local search failed: {e}")
        return JsonResponse(
            {"status": "error", "source": "openalex_local", "error": error_msg},
            status=500,
        )


# EOF
