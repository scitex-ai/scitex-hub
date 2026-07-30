#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Public App API URLs

REST API endpoints:
- Server status, health, versions, and metrics
- Visitor pool management
- MCP tools
- Research tools API (image metadata, docx2tex)
- Statistical analysis
- Plot generation
"""

from django.urls import path

from .. import api_views, views

urlpatterns = [
    # Status API endpoints
    path("api/public-status/", views.public_status_api, name="public-status-api"),
    path("api/server-status/", views.server_status_api, name="server_status_api"),
    path(
        "api/server-health/",
        views.server_health_status_api,
        name="server_health_status_api",
    ),
    path("api/versions/", views.versions_api, name="versions_api"),
    path(
        "api/server-metrics/history/",
        views.server_metrics_history_api,
        name="server_metrics_history",
    ),
    path(
        "api/server-metrics/export/",
        views.server_metrics_export_csv,
        name="server_metrics_export",
    ),
    # Chart data for /server-status/. Replaces the old
    # api/server-metrics/chart/<metric_type>/ PNG route, whose Celery
    # pre-generation wrote into a non-shared container path and therefore
    # answered 503 for its entire life (removed 2026-07-30).
    path(
        "api/server-metrics/series/",
        views.server_metrics_series_api,
        name="server_metrics_series",
    ),
    # Visitor pool API
    path(
        "api/visitor-pool/initialize/",
        views.visitor_pool_initialize_api,
        name="visitor_pool_initialize_api",
    ),
    path(
        "api/visitor-pool/fill-slots/",
        views.visitor_fill_slots_api,
        name="visitor_fill_slots_api",
    ),
    path(
        "api/visitor-pool/free-slots/",
        views.visitor_free_slots_api,
        name="visitor_free_slots_api",
    ),
    path(
        "api/visitor/heartbeat/",
        views.visitor_heartbeat_api,
        name="visitor_heartbeat_api",
    ),
    path(
        "api/visitor/resources/",
        views.visitor_resources_api,
        name="visitor_resources_api",
    ),
    # MCP tools API
    path(
        "api/mcp/tools/",
        api_views.mcp_tools_api,
        name="api_mcp_tools",
    ),
    # Research tools API
    path(
        "api/read-image-metadata/",
        api_views.read_image_metadata,
        name="api_read_image_metadata",
    ),
    path(
        "api/docx2tex/",
        api_views.docx2tex_convert,
        name="api_docx2tex",
    ),
    # Statistical analysis API
    path(
        "api/stats/calculate/",
        api_views.stats_calculate,
        name="api_stats_calculate",
    ),
    path(
        "api/stats/describe/",
        api_views.stats_describe,
        name="api_stats_describe",
    ),
    path(
        "api/stats/recommend/",
        api_views.stats_recommend,
        name="api_stats_recommend",
    ),
    path(
        "api/stats/effect-size/",
        api_views.stats_effect_size,
        name="api_stats_effect_size",
    ),
    path(
        "api/stats/posthoc/",
        api_views.stats_posthoc,
        name="api_stats_posthoc",
    ),
    path(
        "api/stats/power/",
        api_views.stats_power,
        name="api_stats_power",
    ),
    path(
        "api/stats/correct/",
        api_views.stats_correct,
        name="api_stats_correct",
    ),
    path(
        "api/stats/flowchart/",
        api_views.stats_flowchart,
        name="api_stats_flowchart",
    ),
    path(
        "api/stats/plot/",
        api_views.stats_plot,
        name="api_stats_plot",
    ),
    # Plot generation API
    path(
        "api/plot/",
        api_views.plot_endpoint,
        name="api_plot",
    ),
]

# EOF
