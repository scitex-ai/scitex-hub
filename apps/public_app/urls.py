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
    # path("vision/", views.vision, name="vision"),
    path("publications/", views.publications, name="publications"),
    path("contributors/", views.contributors, name="contributors"),
    path("pricing/", views.pricing, name="pricing"),
    # Support pages
    path("donate/", views.donate, name="donate"),
    # Legal and contact pages
    path("contact/", views.contact, name="contact"),
    path("privacy/", views.privacy_policy, name="privacy"),
    path("terms/", views.terms_of_use, name="terms"),
    path("cookies/", views.cookie_policy, name="cookies"),
    # Demo page
    path("demo/", views.demo, name="demo"),
    # Status pages
    path("server-status/", views.server_status, name="server_status"),
    path("api/server-status/", views.server_status_api, name="server_status_api"),
    path("api/server-metrics/history/", views.server_metrics_history_api, name="server_metrics_history"),
    path("api/server-metrics/export/", views.server_metrics_export_csv, name="server_metrics_export"),
    path("api/server-metrics/chart/<str:metric_type>/", views.render_metric_chart, name="server_metrics_chart"),
    path("visitor-status/", views.visitor_status, name="visitor_status"),
    path("visitor-expired/", views.visitor_expired, name="visitor_expired"),
    path("visitor-restart/", views.visitor_restart_session, name="visitor_restart"),
    # API Documentation
    path("api-docs/", views.api_docs, name="api-docs"),
    # SciTeX API Key Management
    path("api-keys/", views.scitex_api_keys, name="scitex_api_keys"),
    # Release Notes
    path("releases/", views.releases_view, name="releases"),
    # Research Tools
    path("tools/", views.tools, name="tools"),
    path(
        "tools/element-inspector/",
        views.tool_element_inspector,
        name="tool_element_inspector",
    ),
    path(
        "tools/asta-citation-scraper/",
        views.tool_asta_citation_scraper,
        name="tool_asta_citation_scraper",
    ),
    path(
        "tools/image-concatenator/",
        views.tool_image_concatenator,
        name="tool_image_concatenator",
    ),
    path(
        "tools/qr-code-generator/",
        views.tool_qr_code_generator,
        name="tool_qr_code_generator",
    ),
    path(
        "tools/color-picker/",
        views.tool_color_picker,
        name="tool_color_picker",
    ),
    path(
        "tools/markdown-renderer/",
        views.tool_markdown_renderer,
        name="tool_markdown_renderer",
    ),
    path(
        "tools/text-diff-checker/",
        views.tool_text_diff_checker,
        name="tool_text_diff_checker",
    ),
    path(
        "tools/images-to-gif/",
        views.tool_images_to_gif,
        name="tool_images_to_gif",
    ),
    path(
        "tools/image-converter/",
        views.tool_image_converter,
        name="tool_image_converter",
    ),
    path(
        "tools/pdf-merger/",
        views.tool_pdf_merger,
        name="tool_pdf_merger",
    ),
    path(
        "tools/statistics-calculator/",
        views.tool_statistics_calculator,
        name="tool_statistics_calculator",
    ),
    path(
        "tools/pdf-splitter/",
        views.tool_pdf_splitter,
        name="tool_pdf_splitter",
    ),
    path(
        "tools/image-resizer/",
        views.tool_image_resizer,
        name="tool_image_resizer",
    ),
    path(
        "tools/repo-concatenator/",
        views.tool_repo_concatenator,
        name="tool_repo_concatenator",
    ),
    path(
        "tools/json-formatter/",
        views.tool_json_formatter,
        name="tool_json_formatter",
    ),
    path(
        "tools/images-to-pdf/",
        views.tool_images_to_pdf,
        name="tool_images_to_pdf",
    ),
    path(
        "tools/pdf-to-images/",
        views.tool_pdf_to_images,
        name="tool_pdf_to_images",
    ),
    path(
        "tools/pdf-compressor/",
        views.tool_pdf_compressor,
        name="tool_pdf_compressor",
    ),
    path(
        "tools/video-editor/",
        views.tool_video_editor,
        name="tool_video_editor",
    ),
    path(
        "tools/plot-viewer/",
        views.tool_plot_viewer,
        name="tool_plot_viewer",
    ),
    path(
        "tools/plot-backend-test/",
        views.tool_plot_backend_test,
        name="tool_plot_backend_test",
    ),
    path(
        "tools/image-viewer/",
        views.tool_image_viewer,
        name="tool_image_viewer",
    ),
    path(
        "tools/mermaid-renderer/",
        views.tool_mermaid_renderer,
        name="tool_mermaid_renderer",
    ),
    # API endpoints
    path(
        "api/read-image-metadata/",
        api_views.read_image_metadata,
        name="api_read_image_metadata",
    ),
]

# EOF
