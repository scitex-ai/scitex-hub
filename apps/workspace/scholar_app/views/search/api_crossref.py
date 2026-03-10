#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/search/api_crossref.py
# Extracted from api_search.py for maintainability
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/scholar_app/views/search/api_crossref.py"
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
def api_search_crossref(request):
    """API endpoint for CrossRef remote API search."""
    query = request.GET.get("q", "").strip()
    max_results = min(int(request.GET.get("max_results", 50)), 100)
    ignore_cache = request.GET.get("ignore_cache", "").lower() == "true"

    if not query:
        return JsonResponse({"error": "Query parameter required"}, status=400)

    # Check cache
    cache_key = (
        f"crossref_search_{hashlib.md5(f'{query}_{max_results}'.encode()).hexdigest()}"
    )
    if not ignore_cache:
        cached = cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return JsonResponse(cached)

    try:
        # CrossRef API: https://api.crossref.org/works
        url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "rows": max_results,
            "select": "DOI,title,author,published-print,published-online,container-title,is-referenced-by-count,abstract,URL,license,link",
        }
        headers = {
            "User-Agent": "SciTeX/1.0 (https://scitex.ai; mailto:contact@scitex.ai)"
        }

        response = requests.get(url, params=params, headers=headers, timeout=180)
        response.raise_for_status()
        data = response.json()

        results = _parse_crossref_results(data, query)

        from .config import get_limit_for_source

        result_count = len(results)
        configured_max = get_limit_for_source(
            "crossref", request.user if request.user.is_authenticated else None
        )

        response_data = {
            "status": "success",
            "source": "crossref",
            "query": query,
            "count": result_count,
            "results": results,
            "result_guidance": _build_result_guidance(
                source_name="crossref",
                received=result_count,
                requested=max_results,
                configured_max=configured_max,
            ),
        }
        cache.set(cache_key, response_data, 1800)
        return JsonResponse(response_data)
    except Exception as e:
        logger.error(f"CrossRef API search failed: {e}")
        return JsonResponse(
            {"status": "error", "source": "crossref", "error": str(e)}, status=500
        )


def _parse_crossref_results(data, query):
    """Parse CrossRef API response into standard format."""
    results = []
    for item in data.get("message", {}).get("items", []):
        # Extract year from published date
        year = None
        for date_field in ["published-print", "published-online"]:
            if item.get(date_field, {}).get("date-parts"):
                date_parts = item[date_field]["date-parts"][0]
                if date_parts:
                    year = date_parts[0]
                    break

        # Format authors
        authors = []
        for author in item.get("author", []):
            name = f"{author.get('given', '')} {author.get('family', '')}".strip()
            if name:
                authors.append(name)

        # Extract title safely (CrossRef returns title as list)
        title_list = item.get("title") or []
        title = title_list[0].strip() if title_list and title_list[0] else ""

        # Skip papers without titles
        if not title:
            continue

        # Extract journal safely
        journal_list = item.get("container-title") or []
        journal = journal_list[0] if journal_list else ""

        # Detect open access from license info
        is_open_access, pdf_url = _detect_open_access(item)

        # Get impact factor for journal
        impact_factor = get_journal_impact_factor(journal) if journal else None

        results.append(
            {
                "title": title,
                "authors": ", ".join(authors),
                "year": year,
                "journal": journal,
                "doi": item.get("DOI") or "",
                "citations": item.get("is-referenced-by-count", 0),
                "abstract": item.get("abstract") or "",
                "externalUrl": item.get("URL") or "",
                "source": "crossref",
                "is_open_access": is_open_access,
                "pdf_url": pdf_url,
                "impact_factor": impact_factor,
            }
        )

    return results


def _detect_open_access(item):
    """Detect open access status from CrossRef item."""
    is_open_access = False
    pdf_url = ""

    licenses = item.get("license") or []
    for lic in licenses:
        lic_url = lic.get("URL", "").lower()
        if any(
            oa in lic_url
            for oa in ["creativecommons.org", "cc-by", "open-access", "public-domain"]
        ):
            is_open_access = True
            break

    links = item.get("link") or []
    for link in links:
        content_type = link.get("content-type", "")
        if "pdf" in content_type.lower():
            pdf_url = link.get("URL", "")
            if pdf_url:
                is_open_access = True
            break

    return is_open_access, pdf_url
