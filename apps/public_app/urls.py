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
    # API documentation
    path("api-docs/", views.api_docs, name="api-docs"),
    path(
        "api-docs/<str:section>/",
        views.api_docs_section,
        name="api-docs-section",
    ),
    path(
        "api-docs/scitex-cloud-api-docs.<str:fmt>",
        views.api_docs_download,
        name="api-docs-download",
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
        "tools/inspect-element/",
        views.tool_element_inspector,
        name="tool_element_inspector",
    ),
    path(
        "tools/scrape-citations/",
        views.tool_asta_citation_scraper,
        name="tool_asta_citation_scraper",
    ),
    path(
        "tools/concat-images/",
        views.tool_image_concatenator,
        name="tool_image_concatenator",
    ),
    path(
        "tools/generate-qr/",
        views.tool_qr_code_generator,
        name="tool_qr_code_generator",
    ),
    path(
        "tools/pick-color/",
        views.tool_color_picker,
        name="tool_color_picker",
    ),
    path(
        "tools/render-md/",
        views.tool_markdown_renderer,
        name="tool_markdown_renderer",
    ),
    path(
        "tools/diff-texts/",
        views.tool_text_diff_checker,
        name="tool_text_diff_checker",
    ),
    path(
        "tools/convert-images-to-gif/",
        views.tool_images_to_gif,
        name="tool_images_to_gif",
    ),
    path(
        "tools/convert-image-format/",
        views.tool_image_converter,
        name="tool_image_converter",
    ),
    path(
        "tools/merge-pdf/",
        views.tool_pdf_merger,
        name="tool_pdf_merger",
    ),
    path(
        "tools/calc-stats/",
        views.tool_statistics_calculator,
        name="tool_statistics_calculator",
    ),
    path(
        "tools/split-pdf/",
        views.tool_pdf_splitter,
        name="tool_pdf_splitter",
    ),
    path(
        "tools/resize-image/",
        views.tool_image_resizer,
        name="tool_image_resizer",
    ),
    path(
        "tools/crop-images/",
        views.tool_image_cropper,
        name="tool_image_cropper",
    ),
    path(
        "tools/concat-repo/",
        views.tool_repo_concatenator,
        name="tool_repo_concatenator",
    ),
    path(
        "tools/format-json/",
        views.tool_json_formatter,
        name="tool_json_formatter",
    ),
    path(
        "tools/convert-images-to-pdf/",
        views.tool_images_to_pdf,
        name="tool_images_to_pdf",
    ),
    path(
        "tools/convert-pdf-to-images/",
        views.tool_pdf_to_images,
        name="tool_pdf_to_images",
    ),
    path(
        "tools/compress-pdf/",
        views.tool_pdf_compressor,
        name="tool_pdf_compressor",
    ),
    path(
        "tools/edit-video/",
        views.tool_video_editor,
        name="tool_video_editor",
    ),
    path(
        "tools/view-plot/",
        views.tool_plot_viewer,
        name="tool_plot_viewer",
    ),
    path(
        "tools/test-plot/",
        views.tool_plot_backend_test,
        name="tool_plot_backend_test",
    ),
    path(
        "tools/view-image/",
        views.tool_image_viewer,
        name="tool_image_viewer",
    ),
    path(
        "tools/render-mmd/",
        views.tool_mermaid_renderer,
        name="tool_mermaid_renderer",
    ),
    path(
        "tools/convert-docx-to-latex/",
        views.tool_docx2tex,
        name="tool_docx2tex",
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
]

# EOF
