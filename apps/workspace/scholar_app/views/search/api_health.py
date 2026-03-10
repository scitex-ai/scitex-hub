#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2026-02-05
# File: apps/scholar_app/views/search/api_health.py
"""Health check endpoints for local database services.

Provides simple health checks for crossref-scitex and openalex-scitex databases.
Can be called via: curl http://localhost:8000/scholar/api/health/crossref-local/
"""

from __future__ import annotations

import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def api_health_crossref_local(request):
    """Health check for CrossRef Local (SciTeX) database.

    Returns:
        200: Service healthy (module importable with search function)
        503: Service unavailable
    """
    try:
        from scitex.scholar.local_dbs import crossref_scitex

        # Check if module has required functions (don't actually query - too slow)
        has_search = hasattr(crossref_scitex, "search")
        has_get = hasattr(crossref_scitex, "get")

        if not has_search:
            return JsonResponse(
                {
                    "status": "unavailable",
                    "service": "crossref-scitex",
                    "error": "Module missing 'search' function",
                    "ready": False,
                },
                status=503,
            )

        return JsonResponse(
            {
                "status": "healthy",
                "service": "crossref-scitex",
                "ready": True,
                "functions": {"search": has_search, "get": has_get},
            }
        )
    except ImportError as e:
        logger.warning(f"crossref-scitex not installed: {e}")
        return JsonResponse(
            {
                "status": "unavailable",
                "service": "crossref-scitex",
                "error": "Package not installed",
                "detail": str(e),
                "ready": False,
            },
            status=503,
        )
    except Exception as e:
        logger.exception(f"CrossRef health check failed: {e}")
        return JsonResponse(
            {
                "status": "unhealthy",
                "service": "crossref-scitex",
                "error": str(e),
                "ready": False,
            },
            status=503,
        )


@require_http_methods(["GET"])
def api_health_openalex_local(request):
    """Health check for OpenAlex Local (SciTeX) database.

    Returns:
        200: Service healthy (module importable with search function)
        503: Service unavailable
    """
    try:
        from scitex.scholar.local_dbs import openalex_scitex

        # Check if module has required functions (don't actually query - too slow)
        has_search = hasattr(openalex_scitex, "search")
        has_get = hasattr(openalex_scitex, "get")

        if not has_search:
            return JsonResponse(
                {
                    "status": "unavailable",
                    "service": "openalex-scitex",
                    "error": "Module missing 'search' function",
                    "ready": False,
                },
                status=503,
            )

        return JsonResponse(
            {
                "status": "healthy",
                "service": "openalex-scitex",
                "ready": True,
                "functions": {"search": has_search, "get": has_get},
            }
        )
    except ImportError as e:
        logger.warning(f"openalex-scitex not installed: {e}")
        return JsonResponse(
            {
                "status": "unavailable",
                "service": "openalex-scitex",
                "error": "Package not installed",
                "detail": str(e),
                "ready": False,
            },
            status=503,
        )
    except Exception as e:
        logger.exception(f"OpenAlex health check failed: {e}")
        return JsonResponse(
            {
                "status": "unhealthy",
                "service": "openalex-scitex",
                "error": str(e),
                "ready": False,
            },
            status=503,
        )


@require_http_methods(["GET"])
def api_health_all_local(request):
    """Combined health check for all local databases.

    Returns:
        200: All services status (may include unhealthy services)
    """
    services = {}

    # Check CrossRef (module availability only - no database query)
    try:
        from scitex.scholar.local_dbs import crossref_scitex

        if hasattr(crossref_scitex, "search"):
            services["crossref-scitex"] = {"status": "healthy", "ready": True}
        else:
            services["crossref-scitex"] = {
                "status": "unavailable",
                "error": "Missing search function",
                "ready": False,
            }
    except Exception as e:
        services["crossref-scitex"] = {
            "status": "unavailable",
            "error": str(e),
            "ready": False,
        }

    # Check OpenAlex (module availability only - no database query)
    try:
        from scitex.scholar.local_dbs import openalex_scitex

        if hasattr(openalex_scitex, "search"):
            services["openalex-scitex"] = {"status": "healthy", "ready": True}
        else:
            services["openalex-scitex"] = {
                "status": "unavailable",
                "error": "Missing search function",
                "ready": False,
            }
    except Exception as e:
        services["openalex-scitex"] = {
            "status": "unavailable",
            "error": str(e),
            "ready": False,
        }

    # Overall status
    all_healthy = all(s.get("status") == "healthy" for s in services.values())

    return JsonResponse(
        {
            "status": "healthy" if all_healthy else "degraded",
            "services": services,
        }
    )


__all__ = [
    "api_health_crossref_local",
    "api_health_openalex_local",
    "api_health_all_local",
]

# EOF
