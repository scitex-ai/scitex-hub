# -*- coding: utf-8 -*-
# Timestamp: 2026-03-09
# File: /home/ywatanabe/proj/scitex-cloud/config/urls_legacy_redirects.py
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
    "workspace",
    "example",
    "notebook",
    "llm",
    "clew",
    # Moved to /apps/ prefix
    "home",
    "hub",
    "discovery",
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
    path(
        "apps/",
        RedirectView.as_view(url="/apps/store/", permanent=True, query_string=True),
    ),
]

# EOF
