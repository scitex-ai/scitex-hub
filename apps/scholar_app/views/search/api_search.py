#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/search/api_search.py
# Main search API module - delegates to specialized modules
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/scholar_app/views/search/api_search.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------
"""
Search API endpoints for scholar module.

This module provides API endpoints for searching academic literature from
multiple sources. The implementation is split across several modules:

- api_utils.py: Shared utilities (cached_search, result guidance)
- api_crossref.py: CrossRef remote API search
- api_crossref_local.py: CrossRef Local (NAS) database search
- api_openalex.py: OpenAlex API search
- api_unified.py: Unified search with command syntax support
- api_syntax_help.py: Search syntax documentation

All view functions are re-exported from this module for backward compatibility.
"""
from django.views.decorators.http import require_http_methods

# Import specialized API endpoints
from .api_crossref import api_search_crossref
from .api_crossref_local import api_search_crossref_local
from .api_openalex import api_search_openalex
from .api_syntax_help import api_search_syntax_help
from .api_unified import api_search_unified

# Import shared utilities
from .api_utils import _build_result_guidance, cached_search

# Import search engines
from .engines import (
    search_arxiv,
    search_biorxiv,
    search_doaj,
    search_plos,
    search_pubmed,
    search_pubmed_central,
    search_semantic_scholar,
)

# =============================================================================
# Simple source-specific API endpoints
# =============================================================================


@require_http_methods(["GET"])
def api_search_arxiv(request):
    """API endpoint for arXiv search only."""
    max_results = min(int(request.GET.get("max_results", 50)), 100)
    return cached_search(request, "arxiv", search_arxiv, max_results)


@require_http_methods(["GET"])
def api_search_pubmed(request):
    """API endpoint for PubMed search only."""
    max_results = min(int(request.GET.get("max_results", 50)), 100)
    return cached_search(request, "pubmed", search_pubmed, max_results)


@require_http_methods(["GET"])
def api_search_semantic(request):
    """API endpoint for Semantic Scholar search only."""
    max_results = min(int(request.GET.get("max_results", 10)), 20)
    return cached_search(
        request, "semantic_scholar", search_semantic_scholar, max_results
    )


@require_http_methods(["GET"])
def api_search_pmc(request):
    """API endpoint for PMC search only."""
    max_results = min(int(request.GET.get("max_results", 50)), 100)
    return cached_search(request, "pmc", search_pubmed_central, max_results)


@require_http_methods(["GET"])
def api_search_doaj(request):
    """API endpoint for DOAJ search only."""
    max_results = min(int(request.GET.get("max_results", 25)), 50)
    return cached_search(request, "doaj", search_doaj, max_results)


@require_http_methods(["GET"])
def api_search_biorxiv(request):
    """API endpoint for bioRxiv search only."""
    max_results = min(int(request.GET.get("max_results", 25)), 50)
    return cached_search(request, "biorxiv", search_biorxiv, max_results)


@require_http_methods(["GET"])
def api_search_plos(request):
    """API endpoint for PLOS search only."""
    max_results = min(int(request.GET.get("max_results", 25)), 50)
    return cached_search(request, "plos", search_plos, max_results)


# =============================================================================
# Export all API endpoints for backward compatibility
# =============================================================================

__all__ = [
    # Utility functions
    "cached_search",
    "_build_result_guidance",
    # Simple source endpoints
    "api_search_arxiv",
    "api_search_pubmed",
    "api_search_semantic",
    "api_search_pmc",
    "api_search_doaj",
    "api_search_biorxiv",
    "api_search_plos",
    # Complex API endpoints (from separate modules)
    "api_search_crossref",
    "api_search_crossref_local",
    "api_search_openalex",
    "api_search_unified",
    "api_search_syntax_help",
]
