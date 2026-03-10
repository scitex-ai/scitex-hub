#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SciTeX Search Integration - modular structure."""

from .pipelines import (
    get_single_pipeline,
    get_parallel_pipeline,
    SCITEX_AVAILABLE,
)
from .filters import django_to_scitex_filters
from .converters import scitex_to_django_paper
from .tracking import track_search_query
from .api_search import api_scitex_search
from .api_search_single import api_scitex_search_single
from .api_capabilities import api_scitex_capabilities

__all__ = [
    # Pipelines
    "get_single_pipeline",
    "get_parallel_pipeline",
    "SCITEX_AVAILABLE",
    # Filters & Converters
    "django_to_scitex_filters",
    "scitex_to_django_paper",
    # Tracking
    "track_search_query",
    # API Views
    "api_scitex_search",
    "api_scitex_search_single",
    "api_scitex_capabilities",
]

# EOF
