#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28 21:31:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/apps/public_app/views/__init__.py
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

# Billing (Stripe scaffold)
from .billing import (
    billing_checkout,
    billing_confirm_card,
    billing_setup_intent,
    cancel_subscription,
    open_billing_portal,
    start_card_setup,
    start_subscription,
    stripe_webhook,
)

# Legal pages
from .legal import (
    contact,
    cookie_policy,
    donate,
    privacy_policy,
    terms_of_use,
    tokushoho,
    tokushoho_en,
)

# Staff-only internal demo library (card hub-internal-demo-video-library-20260917):
# the index is staff-gated inside the view, and the media route serves the same
# directory so internal recordings never need a public static URL.
from .internal_demos import internal_demo_media, internal_demos

# Information pages
from .pages import (
    about,
    contributors,
    demos,
    fundraising,
    keyboard_shortcuts,
    open_source,
    pricing,
    publications,
    recruit,
    security,
    services,
    setup_guide,
    video_player,
)

# SEO views
from .seo import robots_txt

# Status pages
from .status import (
    healthz,
    public_status_api,
    public_status_view,
    server_health_status_api,
    server_metrics_export_csv,
    server_metrics_history_api,
    server_metrics_series_api,
    server_status,
    server_status_api,
    status_api,
    versions_api,
)

# Utility views
from .utils import demo

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
    "internal_demos",
    "internal_demo_media",
    "publications",
    "fundraising",
    "pricing",
    "services",
    "security",
    "contributors",
    "keyboard_shortcuts",
    "recruit",
    # Legal
    "contact",
    "donate",
    "privacy_policy",
    "terms_of_use",
    "cookie_policy",
    "tokushoho",
    "tokushoho_en",
    # Billing
    "billing_checkout",
    "billing_confirm_card",
    "billing_setup_intent",
    "start_card_setup",
    "stripe_webhook",
    "start_subscription",
    "cancel_subscription",
    "open_billing_portal",
    # Status
    "public_status_view",
    "public_status_api",
    "server_status",
    "server_status_api",
    "status_api",
    "healthz",
    "server_health_status_api",
    "server_metrics_history_api",
    "server_metrics_export_csv",
    "server_metrics_series_api",
    "versions_api",
    # API
    "api_docs",
    "api_docs_section",
    "api_docs_download",
    "scitex_api_keys",
    "releases_view",
    # SEO
    "robots_txt",
    # Utils
    "demo",
]

# EOF
