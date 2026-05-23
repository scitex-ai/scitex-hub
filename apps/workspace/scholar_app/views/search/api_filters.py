#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-hub/apps/scholar_app/views/search/api_filters.py
# Filter extraction and formatting utilities for search API
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/scholar_app/views/search/api_filters.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------


def format_results_compact(results):
    """Format results to compact format with only essential fields."""
    return [
        {
            k: r[k]
            for k in [
                "title",
                "authors",
                "year",
                "journal",
                "doi",
                "citations",
                "source",
            ]
            if k in r
        }
        for r in results
    ]


def extract_scitex_filters(parsed):
    """Extract filter information from scitex parsed query."""
    return {
        "positive_keywords": parsed.get("positive_keywords", []),
        "negative_keywords": parsed.get("negative_keywords", []),
        "year_start": parsed.get("year_start"),
        "year_end": parsed.get("year_end"),
        "min_citations": parsed.get("min_citations"),
        "max_citations": parsed.get("max_citations"),
        "min_impact_factor": parsed.get("min_impact_factor"),
        "max_impact_factor": parsed.get("max_impact_factor"),
        "open_access": parsed.get("open_access"),
    }


def extract_django_filters(parsed):
    """Extract filter information from Django parsed query."""
    return {
        "title_includes": parsed.get("title_includes", []),
        "title_excludes": parsed.get("title_excludes", []),
        "author_includes": parsed.get("author_includes", []),
        "author_excludes": parsed.get("author_excludes", []),
        "journal_includes": parsed.get("journal_includes", []),
        "journal_excludes": parsed.get("journal_excludes", []),
        "year_min": parsed.get("year_min"),
        "year_max": parsed.get("year_max"),
        "citations_min": parsed.get("citations_min"),
        "citations_max": parsed.get("citations_max"),
        "impact_factor_min": parsed.get("impact_factor_min"),
        "impact_factor_max": parsed.get("impact_factor_max"),
    }


def get_syntax_help_brief():
    """Get brief syntax help for error messages."""
    return {
        "title_filter": "-t VALUE (include) or -t -VALUE (exclude)",
        "author_filter": "-a VALUE or --author VALUE",
        "journal_filter": "-j VALUE or --journal VALUE",
        "year_range": "-ymin YYYY -ymax YYYY",
        "citations_min": "-cmin N",
        "impact_factor_min": "-ifmin N",
        "example": "neural network -t deep learning -a Smith -ymin 2020",
    }
