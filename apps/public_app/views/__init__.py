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
from .api import (
    api_docs,
    api_docs_download,
    api_docs_section,
    releases_view,
    scitex_api_keys,
)
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
    open_source,
    pricing,
    publications,
    setup_guide,
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
    versions_api,
    visitor_expired,
    visitor_fill_slots_api,
    visitor_free_slots_api,
    visitor_heartbeat_api,
    visitor_pool_full,
    visitor_pool_initialize_api,
    visitor_resources_api,
    visitor_restart_session,
    visitor_status,
)

# Research tools
from .tools import (
    tool_compress_pdf,
    tool_concat_images,
    tool_concat_repo,
    tool_convert_docx_to_latex,
    tool_convert_image_format,
    tool_convert_images_to_gif,
    tool_convert_images_to_pdf,
    tool_convert_pdf_to_images,
    tool_crop_images,
    tool_diff_texts,
    tool_edit_video,
    tool_format_json,
    tool_generate_qr,
    tool_inspect_html_element,
    tool_merge_pdf,
    tool_pick_color,
    tool_render_md,
    tool_render_mmd,
    tool_resize_image,
    tool_run_stats,
    tool_scrape_citations,
    tool_split_pdf,
    tool_test_scitex_plot,
    tool_view_image,
    tool_view_plot,
    tools,
)

# SEO views
from .seo import robots_txt

# Utility views
from .utils import demo, donation_success, send_donation_confirmation

__all__ = [
    # Landing
    "index",
    "premium_subscription",
    # Pages
    "about",
    "setup_guide",
    "demos",
    "open_source",
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
    "versions_api",
    "visitor_status",
    "visitor_restart_session",
    "visitor_expired",
    "visitor_pool_full",
    "visitor_pool_initialize_api",
    "visitor_fill_slots_api",
    "visitor_free_slots_api",
    "visitor_heartbeat_api",
    "visitor_resources_api",
    "render_metric_chart",
    # API
    "api_docs",
    "api_docs_section",
    "api_docs_download",
    "scitex_api_keys",
    "releases_view",
    # Tools
    "tools",
    "tool_compress_pdf",
    "tool_concat_images",
    "tool_concat_repo",
    "tool_convert_docx_to_latex",
    "tool_convert_image_format",
    "tool_convert_images_to_gif",
    "tool_convert_images_to_pdf",
    "tool_convert_pdf_to_images",
    "tool_crop_images",
    "tool_diff_texts",
    "tool_edit_video",
    "tool_format_json",
    "tool_generate_qr",
    "tool_inspect_html_element",
    "tool_merge_pdf",
    "tool_pick_color",
    "tool_render_md",
    "tool_render_mmd",
    "tool_resize_image",
    "tool_run_stats",
    "tool_scrape_citations",
    "tool_split_pdf",
    "tool_test_scitex_plot",
    "tool_view_image",
    "tool_view_plot",
    # SEO
    "robots_txt",
    # Utils
    "demo",
    "donation_success",
    "send_donation_confirmation",
]

# EOF
