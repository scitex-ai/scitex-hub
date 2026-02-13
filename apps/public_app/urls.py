#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-07 22:19:28 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/urls.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/public_app/urls.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

from django.shortcuts import redirect
from django.urls import path

from . import api_views, views

app_name = "public_app"

urlpatterns = [
    path("", views.index, name="index"),
    path("cloud/", lambda request: redirect("public_app:index"), name="cloud"),
    # Concept and vision pages
    path("about/", views.about, name="about"),
    path("open-source/", views.open_source, name="open_source"),
    path("demos/", views.demos, name="demos"),
    path("demos/watch/<str:video_id>/", views.video_player, name="video_player"),
    # path("vision/", views.vision, name="vision"),
    path("publications/", views.publications, name="publications"),
    path("contributors/", views.contributors, name="contributors"),
    path("pricing/", views.pricing, name="pricing"),
    # Reference pages
    path("keyboard-shortcuts/", views.keyboard_shortcuts, name="keyboard_shortcuts"),
    # Support pages
    path("donate/", views.donate, name="donate"),
    # Legal and contact pages
    path("contact/", views.contact, name="contact"),
    path("privacy/", views.privacy_policy, name="privacy"),
    path("terms/", views.terms_of_use, name="terms"),
    path("cookies/", views.cookie_policy, name="cookies"),
    # Demo page
    path("demo/", views.demo, name="demo"),
    # Web API documentation
    path("docs/web-api/", views.api_docs, name="api-docs"),
    path(
        "docs/web-api/<str:section>/",
        views.api_docs_section,
        name="api-docs-section",
    ),
    path(
        "docs/web-api/scitex-cloud-api-docs.<str:fmt>",
        views.api_docs_download,
        name="api-docs-download",
    ),
    # Legacy redirects
    path(
        "api-docs/", lambda r: redirect("public_app:api-docs"), name="api-docs-legacy"
    ),
    path(
        "api-docs/<str:section>/",
        lambda r, section: redirect("public_app:api-docs-section", section=section),
        name="api-docs-section-legacy",
    ),
    # Status pages
    path("server-status/", views.server_status, name="server_status"),
    path("api/server-status/", views.server_status_api, name="server_status_api"),
    path("healthz/", views.healthz, name="healthz"),
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
    path(
        "api/server-metrics/chart/<str:metric_type>/",
        views.render_metric_chart,
        name="server_metrics_chart",
    ),
    path("visitor-status/", views.visitor_status, name="visitor_status"),
    path("visitor-expired/", views.visitor_expired, name="visitor_expired"),
    path("visitor-restart/", views.visitor_restart_session, name="visitor_restart"),
    path("visitor-pool-full/", views.visitor_pool_full, name="visitor_pool_full"),
    path(
        "api/visitor-pool/initialize/",
        views.visitor_pool_initialize_api,
        name="visitor_pool_initialize_api",
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
    # SciTeX API Key Management
    path("api-keys/", views.scitex_api_keys, name="scitex_api_keys"),
    # Release Notes
    path("releases/", views.releases_view, name="releases"),
    # Research Tools
    path("tools/", views.tools, name="tools"),
    path(
        "tools/inspect-html-element/",
        views.tool_inspect_html_element,
        name="tool_inspect_html_element",
    ),
    path(
        "tools/scrape-citations/",
        views.tool_scrape_citations,
        name="tool_scrape_citations",
    ),
    path(
        "tools/concat-images/",
        views.tool_concat_images,
        name="tool_concat_images",
    ),
    path(
        "tools/generate-qr/",
        views.tool_generate_qr,
        name="tool_generate_qr",
    ),
    path(
        "tools/pick-color/",
        views.tool_pick_color,
        name="tool_pick_color",
    ),
    path(
        "tools/render-md/",
        views.tool_render_md,
        name="tool_render_md",
    ),
    path(
        "tools/diff-texts/",
        views.tool_diff_texts,
        name="tool_diff_texts",
    ),
    path(
        "tools/convert-images-to-gif/",
        views.tool_convert_images_to_gif,
        name="tool_convert_images_to_gif",
    ),
    path(
        "tools/convert-image-format/",
        views.tool_convert_image_format,
        name="tool_convert_image_format",
    ),
    path(
        "tools/merge-pdf/",
        views.tool_merge_pdf,
        name="tool_merge_pdf",
    ),
    path(
        "tools/run-stats/",
        views.tool_run_stats,
        name="tool_run_stats",
    ),
    path(
        "tools/split-pdf/",
        views.tool_split_pdf,
        name="tool_split_pdf",
    ),
    path(
        "tools/resize-image/",
        views.tool_resize_image,
        name="tool_resize_image",
    ),
    path(
        "tools/crop-images/",
        views.tool_crop_images,
        name="tool_crop_images",
    ),
    path(
        "tools/concat-repo/",
        views.tool_concat_repo,
        name="tool_concat_repo",
    ),
    path(
        "tools/format-json/",
        views.tool_format_json,
        name="tool_format_json",
    ),
    path(
        "tools/convert-images-to-pdf/",
        views.tool_convert_images_to_pdf,
        name="tool_convert_images_to_pdf",
    ),
    path(
        "tools/convert-pdf-to-images/",
        views.tool_convert_pdf_to_images,
        name="tool_convert_pdf_to_images",
    ),
    path(
        "tools/compress-pdf/",
        views.tool_compress_pdf,
        name="tool_compress_pdf",
    ),
    path(
        "tools/edit-video/",
        views.tool_edit_video,
        name="tool_edit_video",
    ),
    path(
        "tools/view-plot/",
        views.tool_view_plot,
        name="tool_view_plot",
    ),
    path(
        "tools/test-scitex-plot/",
        views.tool_test_scitex_plot,
        name="tool_test_scitex_plot",
    ),
    path(
        "tools/view-image/",
        views.tool_view_image,
        name="tool_view_image",
    ),
    path(
        "tools/render-mmd/",
        views.tool_render_mmd,
        name="tool_render_mmd",
    ),
    path(
        "tools/convert-docx-to-latex/",
        views.tool_convert_docx_to_latex,
        name="tool_convert_docx_to_latex",
    ),
    # API endpoints
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
    path(
        "api/plot/",
        api_views.plot_endpoint,
        name="api_plot",
    ),
]

# EOF
