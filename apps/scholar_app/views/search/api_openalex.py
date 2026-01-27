#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/search/api_openalex.py
# Extracted from api_search.py for maintainability
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/scholar_app/views/search/api_openalex.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------
import hashlib

import requests
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from scitex import logging

from .api_utils import _build_result_guidance
from .citations import get_journal_impact_factor

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def api_search_openalex(request):
    """API endpoint for OpenAlex search."""
    query = request.GET.get("q", "").strip()
    max_results = min(int(request.GET.get("max_results", 50)), 100)
    ignore_cache = request.GET.get("ignore_cache", "").lower() == "true"

    if not query:
        return JsonResponse({"error": "Query parameter required"}, status=400)

    # Check cache
    cache_key = (
        f"openalex_search_{hashlib.md5(f'{query}_{max_results}'.encode()).hexdigest()}"
    )
    if not ignore_cache:
        cached = cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return JsonResponse(cached)

    try:
        # OpenAlex API: https://api.openalex.org/works
        url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "per-page": max_results,
            "select": "id,doi,title,authorships,publication_year,primary_location,cited_by_count,abstract_inverted_index,open_access",
        }
        headers = {
            "User-Agent": "SciTeX/1.0 (https://scitex.ai; mailto:contact@scitex.ai)"
        }

        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        results = _parse_openalex_results(data)

        from .config import get_limit_for_source

        result_count = len(results)
        configured_max = get_limit_for_source(
            "openalex", request.user if request.user.is_authenticated else None
        )

        response_data = {
            "status": "success",
            "source": "openalex",
            "query": query,
            "count": result_count,
            "results": results,
            "result_guidance": _build_result_guidance(
                source_name="openalex",
                received=result_count,
                requested=max_results,
                configured_max=configured_max,
            ),
        }
        cache.set(cache_key, response_data, 1800)
        return JsonResponse(response_data)
    except Exception as e:
        logger.error(f"OpenAlex API search failed: {e}")
        return JsonResponse(
            {"status": "error", "source": "openalex", "error": str(e)}, status=500
        )


def _parse_openalex_results(data):
    """Parse OpenAlex API response into standard format."""
    results = []
    for item in data.get("results", []):
        # Format authors
        authors = []
        for authorship in item.get("authorships", []):
            author = authorship.get("author", {})
            name = author.get("display_name", "")
            if name:
                authors.append(name)

        # Reconstruct abstract from inverted index
        abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))

        # Get journal from primary location
        journal = ""
        primary_loc = item.get("primary_location") or {}
        if primary_loc and primary_loc.get("source"):
            journal = primary_loc["source"].get("display_name", "") or ""

        # Clean DOI
        doi = item.get("doi") or ""
        if doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")

        # Handle title - ensure it's never None and skip papers without titles
        title = (item.get("title") or "").strip()
        if not title:
            continue

        # Get impact factor for journal
        impact_factor = get_journal_impact_factor(journal) if journal else None

        results.append(
            {
                "title": title,
                "authors": ", ".join(authors[:5]) + ("..." if len(authors) > 5 else ""),
                "year": item.get("publication_year"),
                "journal": journal,
                "doi": doi,
                "citations": item.get("cited_by_count", 0),
                "abstract": abstract[:500] + "..." if len(abstract) > 500 else abstract,
                "is_open_access": item.get("open_access", {}).get("is_oa", False),
                "externalUrl": f"https://doi.org/{doi}" if doi else "",
                "source": "openalex",
                "impact_factor": impact_factor,
            }
        )

    return results


def _reconstruct_abstract(abstract_idx):
    """Reconstruct abstract from OpenAlex inverted index format."""
    if not abstract_idx:
        return ""
    try:
        words = [""] * (max(max(positions) for positions in abstract_idx.values()) + 1)
        for word, positions in abstract_idx.items():
            for pos in positions:
                words[pos] = word
        return " ".join(words)
    except (ValueError, TypeError):
        return ""
