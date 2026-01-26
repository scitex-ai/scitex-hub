#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28 21:31:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/views/__init__.py
# ----------------------------------------
from __future__ import annotations

__FILE__ = "./apps/public_app/views/__init__.py"
# ----------------------------------------

"""
Public App Views Package

Exports all view functions for URL routing.
"""

# Landing and marketing pages
# API and developer pages
from .api import api_docs, releases_view, scitex_api_keys
from .landing import index, premium_subscription

# Legal pages
from .legal import contact, cookie_policy, privacy_policy, terms_of_use

# Information pages
from .pages import (
    about,
    contributors,
    demos,
    donate,
    fundraising,
    keyboard_shortcuts,
    pricing,
    publications,
    video_player,
)

# Status pages
from .status import (
    healthz,
    render_metric_chart,
    server_health_status_api,
    server_metrics_export_csv,
    server_metrics_history_api,
    server_status,
    server_status_api,
    visitor_expired,
    visitor_heartbeat_api,
    visitor_pool_full,
    visitor_pool_initialize_api,
    visitor_resources_api,
    visitor_restart_session,
    visitor_status,
)

# Research tools
from .tools import (
    tool_asta_citation_scraper,
    tool_color_picker,
    tool_docx2tex,
    tool_element_inspector,
    tool_image_concatenator,
    tool_image_converter,
    tool_image_resizer,
    tool_image_viewer,
    tool_images_to_gif,
    tool_images_to_pdf,
    tool_json_formatter,
    tool_markdown_renderer,
    tool_mermaid_renderer,
    tool_pdf_compressor,
    tool_pdf_merger,
    tool_pdf_splitter,
    tool_pdf_to_images,
    tool_plot_backend_test,
    tool_plot_viewer,
    tool_qr_code_generator,
    tool_repo_concatenator,
    tool_statistics_calculator,
    tool_text_diff_checker,
    tool_video_editor,
    tools,
)

# Utility views
from .utils import demo, donation_success, send_donation_confirmation

__all__ = [
    # Landing
    "index",
    "premium_subscription",
    # Pages
    "about",
    "demos",
    "video_player",
    "publications",
    "donate",
    "fundraising",
    "pricing",
    "contributors",
    "keyboard_shortcuts",
    # Legal
    "contact",
    "privacy_policy",
    "terms_of_use",
    "cookie_policy",
    # Status
    "server_status",
    "server_status_api",
    "healthz",
    "server_health_status_api",
    "server_metrics_history_api",
    "server_metrics_export_csv",
    "visitor_status",
    "visitor_restart_session",
    "visitor_expired",
    "visitor_pool_full",
    "visitor_pool_initialize_api",
    "visitor_heartbeat_api",
    "visitor_resources_api",
    "render_metric_chart",
    # API
    "api_docs",
    "scitex_api_keys",
    "releases_view",
    # Tools
    "tools",
    "tool_element_inspector",
    "tool_asta_citation_scraper",
    "tool_image_concatenator",
    "tool_qr_code_generator",
    "tool_color_picker",
    "tool_markdown_renderer",
    "tool_text_diff_checker",
    "tool_images_to_gif",
    "tool_image_converter",
    "tool_pdf_merger",
    "tool_statistics_calculator",
    "tool_pdf_splitter",
    "tool_image_resizer",
    "tool_repo_concatenator",
    "tool_json_formatter",
    "tool_images_to_pdf",
    "tool_pdf_to_images",
    "tool_pdf_compressor",
    "tool_video_editor",
    "tool_plot_viewer",
    "tool_plot_backend_test",
    "tool_image_viewer",
    "tool_mermaid_renderer",
    "tool_docx2tex",
    # Utils
    "demo",
    "donation_success",
    "send_donation_confirmation",
]

# EOF
