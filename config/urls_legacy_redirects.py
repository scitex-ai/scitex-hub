# -*- coding: utf-8 -*-
# Timestamp: 2026-03-09
# File: /home/ywatanabe/proj/scitex-hub/config/urls_legacy_redirects.py
"""
Legacy redirect patterns: /<app>/ → /apps/<app>/
Extracted from config/urls.py to eliminate 11 copy-paste blocks.
"""

from __future__ import annotations

from django.urls import path
from django.views.generic import RedirectView

LEGACY_APP_NAMES = [
    "scholar",
    "console",
    "writer",
    "figrecipe",
    "workspace",
    "example",
    "notebook",
    "llm",
    "clew",
    # Moved to /apps/ prefix
    "tools",
    "docs",
]

urlpatterns = [
    path(
        f"{name}/",
        RedirectView.as_view(url=f"/apps/{name}/", permanent=True, query_string=True),
    )
    for name in LEGACY_APP_NAMES
] + [
    # App store: old /apps/apps/ → /apps/store/ (and bare /apps/ → /apps/store/)
    path(
        "apps/apps/",
        RedirectView.as_view(url="/apps/store/", permanent=True, query_string=True),
    ),
    # SDK App Creator wizard moved /create-app/ → /apps/sdk/ (PR #1023 moved
    # it /create-app/ → /apps/new/; sdk-app-gui-parity moves it on to /apps/sdk/).
    # Both old paths redirect straight to the canonical home (no chains).
    path(
        "create-app/",
        RedirectView.as_view(url="/apps/sdk/", permanent=True, query_string=True),
    ),
    path(
        "apps/new/",
        RedirectView.as_view(url="/apps/sdk/", permanent=True, query_string=True),
    ),
    # Journal moved /apps/journal/ → /apps/agentic-journal/ (leaf slug
    # contract, aj-hub-remount-agentic-journal-20261020).
    path(
        "apps/journal/",
        RedirectView.as_view(
            url="/apps/agentic-journal/", permanent=True, query_string=True
        ),
    ),
]

# EOF
