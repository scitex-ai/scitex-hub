#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/search/api_syntax_help.py
# Search syntax documentation endpoint
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/scholar_app/views/search/api_syntax_help.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def api_search_syntax_help(request):
    """
    API endpoint to get search syntax documentation.

    Returns detailed documentation on available search operators and examples.
    """
    return JsonResponse(
        {
            "status": "success",
            "syntax": {
                "title_filter": {
                    "short": "-t",
                    "long": "--title",
                    "description": "Filter by title content",
                    "include_example": "-t neural",
                    "exclude_example": "-t -mouse",
                },
                "author_filter": {
                    "short": "-a",
                    "long": "--author",
                    "description": "Filter by author name",
                    "include_example": "-a Smith",
                    "exclude_example": "-a -Jones",
                },
                "journal_filter": {
                    "short": "-j",
                    "long": "--journal",
                    "description": "Filter by journal name",
                    "include_example": "-j Nature",
                    "exclude_example": "-j -arXiv",
                },
                "year_min": {
                    "short": "-ymin",
                    "long": "--year-min",
                    "description": "Minimum publication year",
                    "example": "-ymin 2020",
                },
                "year_max": {
                    "short": "-ymax",
                    "long": "--year-max",
                    "description": "Maximum publication year",
                    "example": "-ymax 2024",
                },
                "citations_min": {
                    "short": "-cmin",
                    "long": "--citations-min",
                    "description": "Minimum citation count",
                    "example": "-cmin 100",
                },
                "citations_max": {
                    "short": "-cmax",
                    "long": "--citations-max",
                    "description": "Maximum citation count",
                    "example": "-cmax 1000",
                },
                "impact_factor_min": {
                    "short": "-ifmin",
                    "long": "--if-min",
                    "description": "Minimum journal impact factor",
                    "example": "-ifmin 5",
                },
                "impact_factor_max": {
                    "short": "-ifmax",
                    "long": "--if-max",
                    "description": "Maximum journal impact factor",
                    "example": "-ifmax 50",
                },
            },
            "examples": [
                {
                    "query": "neural network -t deep learning -ymin 2020",
                    "description": "Search for 'neural network', title must contain 'deep learning', published since 2020",
                },
                {
                    "query": "CRISPR -a Doudna -j Nature -cmin 100",
                    "description": "Search for 'CRISPR' by author Doudna in Nature journal with at least 100 citations",
                },
                {
                    "query": "cancer treatment -t -mouse -t -rat -ymin 2022",
                    "description": "Search for 'cancer treatment', exclude mouse and rat studies, since 2022",
                },
                {
                    "query": "machine learning -ifmin 10 -cmin 50",
                    "description": "Search 'machine learning' in journals with IF >= 10 and papers with >= 50 citations",
                },
            ],
            "available_sources": [
                "pubmed",
                "arxiv",
                "semantic",
                "crossref",
                "openalex",
                "pmc",
                "doaj",
                "biorxiv",
                "plos",
            ],
            "query_parameters": {
                "q": "Search query with optional command syntax (required)",
                "sources": "Comma-separated list of sources to search (optional)",
                "max_results": "Maximum results per source, 1-100 (default: 20)",
                "format": "'full' or 'compact' response format (default: full)",
            },
        }
    )
