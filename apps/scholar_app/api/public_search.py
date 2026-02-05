#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/scholar_app/api/public_search.py
"""Public Scholar Search API - Rate limited endpoint for external users.

Endpoints:
    GET /api/v1/scholar/search/
        Query params:
            q: Search query (required)
            limit: Max results per source (default: 20, max: 100)
            format: Response format (json, bibtex, csv, text)
            sources: Comma-separated list (pubmed, arxiv, semantic, crossref, openalex)

    GET /api/v1/scholar/info/
        Returns API info and rate limit status

Rate Limits:
    Anonymous: 10 requests/minute
    API Key: 100 requests/minute

API Key Usage:
    Header: X-SCITEX-API-KEY: <your-key>
    Or query param: ?api_key=<your-key>

Example Usage:
    curl "https://scitex.ai/api/v1/scholar/search/?q=neural+networks&limit=10"
    curl "https://scitex.ai/api/v1/scholar/search/?q=cancer&format=bibtex"
    curl "https://scitex.ai/api/v1/scholar/search/?q=covid&sources=pubmed,arxiv&format=csv"
    curl -H "X-SCITEX-API-KEY: your-key" "https://scitex.ai/api/v1/scholar/search/?q=query"
"""

from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse, JsonResponse

from .public_search_formatters import normalize_result, to_bibtex, to_csv, to_text
from .public_search_utils import (
    RATE_LIMIT_ANONYMOUS,
    RATE_LIMIT_USER,
    rate_limit,
    search_external_sources,
)

logger = logging.getLogger(__name__)


@rate_limit
def search(request: HttpRequest) -> HttpResponse:
    """
    Public search endpoint for academic literature.

    GET /api/v1/scholar/search/?q=<query>&limit=20&format=json

    Query Parameters:
        q: Search query (required)
        limit: Max results per source (default: 20, max: 100)
        format: Response format - json, bibtex, csv, text (default: json)
        sources: Comma-separated sources (default: pubmed,arxiv,semantic)
                 Available: pubmed, arxiv, semantic, crossref, openalex

    Returns:
        JSON, BibTeX, CSV, or plain text depending on format parameter
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    # Parse query
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse(
            {
                "error": "Missing required parameter: q",
                "example": "/api/v1/scholar/search/?q=neural+networks",
                "documentation": "/api/v1/scholar/info/",
            },
            status=400,
        )

    # Parse limit
    try:
        limit = min(int(request.GET.get("limit", 20)), 100)
    except ValueError:
        limit = 20

    # Parse format
    output_format = request.GET.get("format", "json").lower()
    if output_format not in ("json", "bibtex", "csv", "text"):
        return JsonResponse(
            {
                "error": f"Invalid format: {output_format}",
                "valid_formats": ["json", "bibtex", "csv", "text"],
            },
            status=400,
        )

    # Parse sources
    sources_param = request.GET.get("sources", "pubmed,arxiv,semantic")
    valid_sources = {"pubmed", "arxiv", "semantic", "crossref", "openalex"}
    sources = [s.strip().lower() for s in sources_param.split(",")]
    sources = [s for s in sources if s in valid_sources]
    if not sources:
        sources = ["pubmed", "arxiv", "semantic"]

    # Perform search
    try:
        results, source_stats = search_external_sources(query, sources, limit)
        results.sort(key=lambda x: -(x.get("citations") or 0))

        # Format response
        safe_query = "".join(c if c.isalnum() else "_" for c in query[:30])

        if output_format == "bibtex":
            content = to_bibtex(results)
            return HttpResponse(
                content,
                content_type="application/x-bibtex; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="scitex-{safe_query}.bib"'
                },
            )

        if output_format == "csv":
            content = to_csv(results)
            return HttpResponse(
                content,
                content_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="scitex-{safe_query}.csv"'
                },
            )

        if output_format == "text":
            return HttpResponse(
                to_text(results), content_type="text/plain; charset=utf-8"
            )

        # Default: JSON
        return JsonResponse(
            {
                "status": "success",
                "query": query,
                "total_count": len(results),
                "sources": source_stats,
                "results": [normalize_result(r) for r in results],
            }
        )

    except Exception as e:
        logger.exception(f"Search error: {e}")
        return JsonResponse({"error": "Search failed", "detail": str(e)}, status=500)


def info(request: HttpRequest) -> HttpResponse:
    """
    Get API documentation and status.

    GET /api/v1/scholar/info/
    """
    return JsonResponse(
        {
            "status": "ok",
            "api_version": "v1",
            "description": "SciTeX Scholar Public API for academic literature search",
            "endpoints": {
                "search": {
                    "url": "/api/v1/scholar/search/",
                    "method": "GET",
                    "parameters": {
                        "q": {
                            "type": "string",
                            "required": True,
                            "description": "Search query",
                        },
                        "limit": {
                            "type": "integer",
                            "required": False,
                            "default": 20,
                            "max": 100,
                            "description": "Maximum results per source",
                        },
                        "format": {
                            "type": "string",
                            "required": False,
                            "default": "json",
                            "options": ["json", "bibtex", "csv", "text"],
                            "description": "Response format",
                        },
                        "sources": {
                            "type": "string",
                            "required": False,
                            "default": "pubmed,arxiv,semantic",
                            "options": [
                                "pubmed",
                                "arxiv",
                                "semantic",
                                "crossref",
                                "openalex",
                            ],
                            "description": "Comma-separated list of sources",
                        },
                    },
                    "examples": [
                        "/api/v1/scholar/search/?q=neural+networks",
                        "/api/v1/scholar/search/?q=cancer&format=bibtex&limit=50",
                        "/api/v1/scholar/search/?q=covid&sources=pubmed,crossref&format=csv",
                    ],
                },
                "info": {
                    "url": "/api/v1/scholar/info/",
                    "method": "GET",
                    "description": "This endpoint - API documentation",
                },
            },
            "rate_limits": {
                "anonymous": f"{RATE_LIMIT_ANONYMOUS} requests/minute",
                "with_api_key": f"{RATE_LIMIT_USER} requests/minute",
            },
            "authentication": {
                "header": "X-SCITEX-API-KEY: <your-key>",
                "query_param": "?api_key=<your-key>",
                "note": "API keys available at https://scitex.ai/accounts/api-keys/",
            },
            "response_fields": {
                "title": "Paper title",
                "authors": "Author names (comma-separated)",
                "journal": "Journal name",
                "year": "Publication year",
                "doi": "Digital Object Identifier",
                "pmid": "PubMed ID",
                "arxiv_id": "arXiv identifier",
                "citations": "Citation count",
                "impact_factor": "Journal impact factor",
                "is_open_access": "Whether paper is open access",
                "abstract": "Paper abstract",
                "url": "Link to paper",
                "source": "Data source (pubmed, arxiv, etc.)",
            },
        }
    )


# EOF
