#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vis app URLs - Statistics API endpoints (scitex.stats integration)."""

from __future__ import annotations

from django.urls import path

from ..views import api as api_views

# Statistics API endpoints
urlpatterns = [
    # Get applicable tests for right-click context menu
    path(
        "api/stats/applicable/",
        api_views.get_applicable_tests,
        name="api_stats_applicable",
    ),
    # Run a specific statistical test
    path("api/stats/run/", api_views.run_statistical_test, name="api_stats_run"),
    # Run all applicable tests (magic mode)
    path("api/stats/run-all/", api_views.run_all_applicable, name="api_stats_run_all"),
    # Build StatContext from plot metadata
    path(
        "api/stats/context/",
        api_views.build_context_from_plot,
        name="api_stats_context",
    ),
]


# EOF
