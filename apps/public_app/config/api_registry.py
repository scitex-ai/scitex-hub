#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API Registry - Single Source of Truth for all SciTeX APIs.

This registry defines all exposed APIs. Documentation is generated
programmatically from this registry to ensure consistency.

Endpoint definitions live in api_endpoints/ subdirectory, one file per category.
"""

from __future__ import annotations

from .api_endpoints import (
    PLOT_CATEGORY,
    PROJECT_CATEGORY,
    PUBLIC_CATEGORY,
    SCHOLAR_CATEGORY,
    STATS_CATEGORY,
    WRITER_CATEGORY,
)

# API Categories and Endpoints
API_REGISTRY = {
    "public": PUBLIC_CATEGORY,
    "scholar": SCHOLAR_CATEGORY,
    "writer": WRITER_CATEGORY,
    "project": PROJECT_CATEGORY,
    "plot": PLOT_CATEGORY,
    "stats": STATS_CATEGORY,
}

# Rate Limits
RATE_LIMITS = {
    "anonymous": {"limit": 10, "window": "minute", "note": "Public API only"},
    "api_key": {"limit": 100, "window": "minute", "note": "All endpoints"},
    "campaign": {"limit": 100, "window": "minute", "note": "Alpha testing"},
}

# Error Codes
ERROR_CODES = {
    200: "Success",
    400: "Bad Request - Invalid parameters",
    401: "Unauthorized - Missing/invalid auth",
    403: "Forbidden - Insufficient permissions",
    404: "Not Found - Resource doesn't exist",
    429: "Too Many Requests - Rate limit exceeded",
    500: "Server Error - Internal error",
}


def get_all_endpoints():
    """Get flat list of all endpoints."""
    endpoints = []
    for category, info in API_REGISTRY.items():
        for ep in info["endpoints"]:
            endpoints.append(
                {
                    "category": category,
                    "category_name": info["name"],
                    "base_path": info["base_path"],
                    "auth_required": info["auth_required"],
                    **ep,
                }
            )
    return endpoints


def get_endpoints_by_category(category: str):
    """Get endpoints for a specific category."""
    if category not in API_REGISTRY:
        return []
    info = API_REGISTRY[category]
    return [
        {"base_path": info["base_path"], "auth_required": info["auth_required"], **ep}
        for ep in info["endpoints"]
    ]
