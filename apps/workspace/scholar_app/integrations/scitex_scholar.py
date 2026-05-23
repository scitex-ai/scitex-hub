#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-hub/apps/scholar_app/integrations/scitex_scholar.py
"""
Integration layer between Django and scitex.scholar package.

This module provides a bridge between Django views and the scitex.scholar
package, which contains the core search engine logic that works both
locally and in the cloud.

The scitex.scholar package provides:
- SearchQueryParser: Advanced query parsing with filters
- ScholarSearchEngine: Unified search across multiple databases
- Individual search engines: ArXiv, PubMed, CrossRef, Semantic Scholar, OpenAlex
"""

import asyncio
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# Try to import scitex.scholar
try:
    from scitex.scholar import ScholarConfig
    from scitex.scholar.pipelines.SearchQueryParser import SearchQueryParser
    from scitex.scholar.search_engines.ScholarSearchEngine import ScholarSearchEngine

    SCITEX_SCHOLAR_AVAILABLE = True
except ImportError:
    SCITEX_SCHOLAR_AVAILABLE = False
    ScholarConfig = None
    logger.warning(
        "scitex.scholar package not available, falling back to Django-only search"
    )


def get_user_scitex_dir(user, session_key: Optional[str] = None) -> Path:
    """
    Get the user-specific SCITEX directory path.

    Resolution order:
    1. SCITEX_HUB_USER_DATA_ROOT env var (for containerized per-user setups)
       (falls back to legacy SCITEX_USER_DATA_ROOT)
    2. USER_DATA_ROOT Django setting
    3. Default: {BASE_DIR}/data/users/{username}/.scitex

    This provides thread-safe, per-user isolation for scitex.scholar operations.
    NEVER use os.environ["SCITEX_DIR"] directly in multi-user Django - it's not thread-safe.

    Args:
        user: Django User instance or None for anonymous
        session_key: Session key for anonymous users

    Returns:
        Path to user's .scitex directory
    """
    import os

    base_dir = getattr(settings, "BASE_DIR", Path.cwd())

    # Check for containerized setup with per-user $HOME
    # Support both new (SCITEX_HUB_*) and legacy (SCITEX_*) names
    user_data_root = os.environ.get("SCITEX_HUB_USER_DATA_ROOT") or os.environ.get(
        "SCITEX_USER_DATA_ROOT"
    )
    if user_data_root:
        # Containerized environment - use the provided root directly
        # Assumes $HOME or similar is already set per-user
        user_scitex_dir = Path(user_data_root) / ".scitex"
    else:
        # Shared process - use explicit user directory
        user_data_root_setting = getattr(settings, "USER_DATA_ROOT", None)
        if user_data_root_setting:
            base_path = Path(user_data_root_setting)
        else:
            base_path = Path(base_dir) / "data" / "users"

        if user and user.is_authenticated:
            user_scitex_dir = base_path / user.username / ".scitex"
        elif session_key:
            # Anonymous user with session
            user_scitex_dir = (
                Path(base_dir) / "data" / "visitor" / session_key / ".scitex"
            )
        else:
            # Fallback for anonymous without session
            user_scitex_dir = Path(base_dir) / "data" / "visitor" / "shared" / ".scitex"

    user_scitex_dir.mkdir(parents=True, exist_ok=True)
    return user_scitex_dir


def get_scholar_config(user=None) -> Optional["ScholarConfig"]:
    """
    Get a ScholarConfig instance with user-specific paths.

    This is the SAFE way to get ScholarConfig in Django - it passes
    the scholar_dir directly instead of using environment variables.

    Args:
        user: Django User instance or None

    Returns:
        ScholarConfig instance or None if not available
    """
    if not SCITEX_SCHOLAR_AVAILABLE or ScholarConfig is None:
        return None

    user_scitex_dir = get_user_scitex_dir(user)
    return ScholarConfig(scholar_dir=user_scitex_dir)


@lru_cache(maxsize=1)
def get_search_engine(email: Optional[str] = None) -> Optional["ScholarSearchEngine"]:
    """
    Get a cached instance of ScholarSearchEngine.

    Args:
        email: User email for API rate limit benefits

    Returns:
        ScholarSearchEngine instance or None if not available
    """
    if not SCITEX_SCHOLAR_AVAILABLE:
        return None

    return ScholarSearchEngine(
        default_mode="parallel",
        use_cache=True,
        email=email,
    )


def parse_query_scitex(query: str) -> Dict[str, Any]:
    """
    Parse a search query using scitex's SearchQueryParser.

    This is the recommended way to parse queries as it provides
    more advanced syntax than the Django-only implementation.

    Args:
        query: Search query string with optional filters

    Returns:
        Dictionary with parsed filters and keyword query

    Examples:
        >>> parse_query_scitex("hippocampus -seizure year:2020-2024 if:>5")
        {
            'keyword_query': 'hippocampus',
            'positive_keywords': ['hippocampus'],
            'negative_keywords': ['seizure'],
            'year_start': 2020,
            'year_end': 2024,
            'min_impact_factor': 5.0,
            ...
        }
    """
    if not SCITEX_SCHOLAR_AVAILABLE:
        # Fallback to simple parsing
        return {
            "keyword_query": query,
            "positive_keywords": query.split(),
            "negative_keywords": [],
        }

    parser = SearchQueryParser(query)
    filters = parser.get_filters()
    filters["keyword_query"] = parser.get_keyword_query()
    filters["original_query"] = query

    return filters


async def search_async(
    query: str,
    mode: str = "parallel",
    max_results: int = 100,
    email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute an async search using scitex.scholar.

    Args:
        query: Search query (supports advanced syntax)
        mode: 'parallel' or 'single' (sequential)
        max_results: Maximum results per source
        email: User email for rate limit benefits

    Returns:
        Dict with results and metadata
    """
    engine = get_search_engine(email)
    if not engine:
        return {
            "results": [],
            "metadata": {"error": "scitex.scholar not available"},
            "stats": {},
        }

    return await engine.search(
        query=query,
        mode=mode,
        max_results=max_results,
        parse_query=True,
    )


def search_sync(
    query: str,
    mode: str = "parallel",
    max_results: int = 100,
    email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a synchronous search (wrapper for async).

    Args:
        query: Search query
        mode: 'parallel' or 'single'
        max_results: Maximum results per source
        email: User email for rate limit benefits

    Returns:
        Dict with results and metadata
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(search_async(query, mode, max_results, email))


def get_supported_sources() -> List[str]:
    """Get list of supported search sources from scitex."""
    engine = get_search_engine()
    if engine:
        return engine.get_supported_engines()
    return ["pubmed", "arxiv", "semantic_scholar", "crossref", "openalex"]


def get_engine_statistics() -> Dict[str, Any]:
    """Get search engine statistics."""
    engine = get_search_engine()
    if engine:
        return engine.get_statistics()
    return {}


def is_available() -> bool:
    """Check if scitex.scholar is available."""
    return SCITEX_SCHOLAR_AVAILABLE


# Mapping between Django filter names and scitex filter names
FILTER_MAPPING = {
    # Django name -> scitex name
    "year_min": "year_start",
    "year_max": "year_end",
    "citations_min": "min_citations",
    "citations_max": "max_citations",
    "impact_factor_min": "min_impact_factor",
    "impact_factor_max": "max_impact_factor",
    "title_includes": "positive_keywords",
    "title_excludes": "negative_keywords",
}


def convert_django_filters_to_scitex(django_filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Django filter format to scitex filter format.

    Args:
        django_filters: Filters from Django parse_query_operators

    Returns:
        Filters compatible with scitex.scholar
    """
    scitex_filters = {}

    for django_key, value in django_filters.items():
        if django_key in FILTER_MAPPING:
            scitex_key = FILTER_MAPPING[django_key]
            scitex_filters[scitex_key] = value
        else:
            scitex_filters[django_key] = value

    return scitex_filters


def convert_scitex_results_to_django(
    scitex_results: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Convert scitex search results to Django SearchIndex-compatible format.

    Args:
        scitex_results: Results from ScholarSearchEngine.search()

    Returns:
        List of paper dictionaries compatible with Django templates
    """
    if not scitex_results or "results" not in scitex_results:
        return []

    django_results = []
    for paper in scitex_results["results"]:
        # Skip papers without titles
        title = (paper.get("title") or "").strip()
        if not title:
            continue
        django_results.append(
            {
                "id": paper.get("id"),
                "title": title,
                "authors": paper.get("authors", ""),
                "abstract": paper.get("abstract", ""),
                "journal": paper.get("journal", ""),
                "year": paper.get("year") or paper.get("publication_year"),
                "doi": paper.get("doi"),
                "pmid": paper.get("pmid"),
                "arxiv_id": paper.get("arxiv_id"),
                "url": paper.get("url") or paper.get("external_url"),
                "pdf_url": paper.get("pdf_url"),
                "source": paper.get("source", "scitex"),
                "citations": paper.get("citations") or paper.get("citation_count"),
                "impact_factor": paper.get("impact_factor"),
                "open_access": paper.get("open_access", False),
            }
        )

    return django_results


# EOF
