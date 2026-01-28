#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/search/api_crossref_local.py
# CrossRef Local (NAS) database search endpoint
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/scholar_app/views/search/api_crossref_local.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------
import hashlib

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from scitex import logging

from .api_utils import _build_result_guidance
from .citations import get_journal_impact_factor

logger = logging.getLogger(__name__)

# CrossRef Local API URL (internal Docker network)
CROSSREF_LOCAL_URL = os.environ.get("CROSSREF_LOCAL_API_URL", "http://crossref:3333")


@require_http_methods(["GET"])
def api_search_crossref_local(request):
    """API endpoint for CrossRef Local (NAS database) search."""
    query = request.GET.get("q", "").strip()
    max_results = min(int(request.GET.get("max_results", 50)), 100)
    ignore_cache = request.GET.get("ignore_cache", "").lower() == "true"

    if not query:
        return JsonResponse({"error": "Query parameter required"}, status=400)

    # Check cache
    cache_key = f"crossref_local_search_{hashlib.md5(f'{query}_{max_results}'.encode()).hexdigest()}"
    if not ignore_cache:
        cached = cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return JsonResponse(cached)

    try:
        # CrossRef Local API
        url = f"{CROSSREF_LOCAL_URL}/api/search/"
        params = {
            "title": query,
            "limit": max_results,
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        results = _parse_crossref_local_results(data, query)

        from .config import get_limit_for_source
        result_count = len(results)
        configured_max = get_limit_for_source(
            "crossref_local", request.user if request.user.is_authenticated else None
        )

        response_data = {
            "status": "success",
            "source": "crossref_local",
            "query": query,
            "count": result_count,
            "results": results,
            "result_guidance": _build_result_guidance(
                source_name="crossref_local",
                received=result_count,
                requested=max_results,
                configured_max=configured_max,
            ),
        }
        cache.set(cache_key, response_data, 1800)
        return JsonResponse(response_data)
    except requests.exceptions.ConnectionError:
        logger.warning("CrossRef Local service not available")
        return JsonResponse(
            {
                "status": "error",
                "source": "crossref_local",
                "error": "CrossRef Local service not available",
            },
            status=503,
        )
    except Exception as e:
        logger.error(f"CrossRef Local search failed: {e}")
        return JsonResponse(
            {"status": "error", "source": "crossref_local", "error": str(e)}, status=500
        )


def _parse_crossref_local_results(data, query):
    """Parse CrossRef Local API response into standard format."""
    results = []
    items = data.get("results", data) if isinstance(data, dict) else data

    if not isinstance(items, list):
        items = [items] if items else []

    for item in items:
        if not isinstance(item, dict):
            continue

        # Extract title
        title = item.get("title") or ""
        if isinstance(title, list):
            title = title[0] if title else ""
        title = str(title).strip()

        if not title:
            continue

        # Extract year
        year = item.get("year") or item.get("published_year")
        if not year:
            published = item.get("published") or item.get("published_print") or {}
            if isinstance(published, dict) and published.get("date-parts"):
                date_parts = published["date-parts"]
                if date_parts and date_parts[0]:
                    year = date_parts[0][0]

        # Format authors
        authors = []
        author_data = item.get("authors") or item.get("author") or []
        if isinstance(author_data, str):
            authors = [author_data]
        elif isinstance(author_data, list):
            for author in author_data:
                if isinstance(author, str):
                    authors.append(author)
                elif isinstance(author, dict):
                    name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                    if not name:
                        name = author.get("name", "")
                    if name:
                        authors.append(name)

        # Extract journal
        journal = item.get("journal") or item.get("container_title") or item.get("container-title") or ""
        if isinstance(journal, list):
            journal = journal[0] if journal else ""

        # Extract DOI
        doi = item.get("doi") or item.get("DOI") or ""
        if doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")

        # Get impact factor
        impact_factor = get_journal_impact_factor(journal) if journal else None

        results.append({
            "title": title,
            "authors": ", ".join(authors[:5]) + ("..." if len(authors) > 5 else ""),
            "year": year,
            "journal": journal,
            "doi": doi,
            "citations": item.get("citations") or item.get("is_referenced_by_count") or item.get("is-referenced-by-count") or 0,
            "abstract": item.get("abstract") or "",
            "externalUrl": f"https://doi.org/{doi}" if doi else "",
            "source": "crossref_local",
            "is_open_access": item.get("is_open_access", False),
            "pdf_url": item.get("pdf_url") or "",
            "impact_factor": impact_factor,
        })

    return results
