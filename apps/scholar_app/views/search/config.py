#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/scholar_app/views/search/config.py
"""
Search configuration and limits.

Centralized configuration for search parameters across all engines.
These values are used both in backend search logic and displayed to users.
User-specific limits can override defaults via UserPreference.search_limits.

Environment variables:
    SCITEX_SEARCH_LIMIT_LOCAL: Override limit for local databases (default: 10000 prod, 2000 dev)
    SCITEX_ENV: Environment name ('dev', 'nas') - affects default limits
"""

from __future__ import annotations

import os

# Special value for "no limit" - internally mapped to a practical maximum
NO_LIMIT = -1
PRACTICAL_MAX_LIMIT = 50000  # Internal cap when NO_LIMIT is used

# Environment-based limits: Both NAS and dev can handle 10000 results
# (openalex-local/crossref-local relay servers are fast: ~50ms for full-text search)
_ENV = os.environ.get("SCITEX_ENV", "dev")
_DEFAULT_LOCAL_LIMIT = 10000  # Both environments: relay servers are fast enough
LOCAL_DB_LIMIT = int(os.environ.get("SCITEX_SEARCH_LIMIT_LOCAL", _DEFAULT_LOCAL_LIMIT))

# Default search result limits per source (can be overridden per user)
# Use -1 for "no limit" (will use PRACTICAL_MAX_LIMIT internally)
# These are the maximum results fetched from each source per search
DEFAULT_SEARCH_LIMITS = {
    # === LOCAL DATABASES (Fast, Recommended) ===
    "crossref_local": {
        "name": "Crossref (SciTeX)",
        "limit": LOCAL_DB_LIMIT,  # Env-based: NAS=10000 (fast SQLite), dev=2000 (HTTP API)
        "description": "CrossRef SQLite DB (~47M citations) - Recommended",
        "category": "local",
        "recommended": True,
    },
    "openalex_local": {
        "name": "OpenAlex (SciTeX)",
        "limit": LOCAL_DB_LIMIT,  # Env-based: NAS=10000 (fast SQLite), dev=2000 (HTTP API)
        "description": "OpenAlex SQLite DB (~284M works) - Recommended",
        "category": "local",
        "recommended": True,
    },
    "database": {
        "name": "Cache",
        "limit": 50,
        "description": "Previously searched results",
        "category": "local",
        "recommended": False,
    },
    # === EXTERNAL APIs (Slower, Rate Limited) ===
    "pubmed": {
        "name": "PubMed",
        "limit": 100,
        "description": "NCBI PubMed API (external)",
        "category": "external",
        "recommended": False,
    },
    "arxiv": {
        "name": "arXiv",
        "limit": 100,
        "description": "arXiv preprint server (external)",
        "category": "external",
        "recommended": False,
    },
    "semantic_scholar": {
        "name": "Semantic Scholar",
        "limit": 50,
        "description": "Semantic Scholar API (external, rate limited)",
        "category": "external",
        "recommended": False,
    },
    "crossref": {
        "name": "Crossref API",
        "limit": 100,
        "description": "CrossRef remote API (external)",
        "category": "external",
        "recommended": False,
    },
    "openalex": {
        "name": "OpenAlex API",
        "limit": 100,
        "description": "OpenAlex remote API (external)",
        "category": "external",
        "recommended": False,
    },
    "scitex_pipeline": {
        "name": "SciTeX Pipeline",
        "limit": 200,
        "description": "Combined parallel search",
        "category": "special",
        "recommended": False,
    },
}

# Overall result cap (can be increased for local sources)
OVERALL_RESULT_CAP = 100000

# Default filter ranges
DEFAULT_FILTER_RANGES = {
    "year_min": 1900,
    "year_max": 2026,
    "citations_min": 0,
    "citations_max": 128,
    "impact_factor_min": 0,
    "impact_factor_max": 50.0,
}


def resolve_limit(limit: int) -> int:
    """Resolve limit value, converting NO_LIMIT (-1) to practical maximum."""
    if limit == NO_LIMIT or limit < 0:
        return PRACTICAL_MAX_LIMIT
    return limit


def get_search_limits_for_user(user=None):
    """
    Get search limits for a user, merging defaults with user overrides.

    Args:
        user: Django User object (optional). If None, returns defaults.

    Returns:
        dict: Search limits with user overrides applied.
    """
    import copy

    limits = copy.deepcopy(DEFAULT_SEARCH_LIMITS)

    if user and user.is_authenticated:
        try:
            from ...models import UserPreference

            prefs = UserPreference.get_or_create_for_user(user)
            user_limits = prefs.search_limits or {}

            # Override defaults with user-specific limits
            for source_key, user_limit in user_limits.items():
                if source_key in limits and isinstance(user_limit, int):
                    limits[source_key]["limit"] = user_limit
        except Exception:
            pass  # Fall back to defaults on any error

    return limits


def get_search_limits_for_template(user=None):
    """
    Get search limits formatted for template display.

    Args:
        user: Django User object (optional). If None, uses defaults.

    Returns:
        list: List of dicts with source name and limit for UI display.
    """
    limits_config = get_search_limits_for_user(user)

    # Order: Local databases first (recommended), then external APIs
    display_order = [
        # Local databases (fast, recommended)
        "crossref_local",
        "openalex_local",
        "database",
        # External APIs (slower, rate limited)
        "pubmed",
        "arxiv",
        "semantic_scholar",
        "crossref",
        "openalex",
    ]

    limits = []
    for key in display_order:
        if key in limits_config:
            config = limits_config[key]
            limit_value = config["limit"]
            # Display -1 as "∞" (unlimited) in UI
            display_limit = "∞" if limit_value == NO_LIMIT else limit_value
            limits.append(
                {
                    "key": key,
                    "name": config["name"],
                    "limit": limit_value,
                    "display_limit": display_limit,
                    "description": config.get("description", ""),
                    "category": config.get("category", "external"),
                    "recommended": config.get("recommended", False),
                }
            )

    return limits


def get_limit_for_source(source_key: str, user=None, resolve: bool = True) -> int:
    """Get the result limit for a specific source.

    Args:
        source_key: The source identifier (e.g., 'crossref_local')
        user: Django User object (optional)
        resolve: If True, converts NO_LIMIT (-1) to PRACTICAL_MAX_LIMIT

    Returns:
        int: The limit value (resolved or raw depending on `resolve` parameter)
    """
    limits = get_search_limits_for_user(user)
    if source_key in limits:
        limit = limits[source_key]["limit"]
        return resolve_limit(limit) if resolve else limit
    return 10  # Default fallback
