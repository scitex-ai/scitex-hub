#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from django.urls import path
from django.views.generic import RedirectView

from apps.unified_app.views.index import unified_content

# Redirect /unified/xxx/ → native module URLs (module tab bar now lives on each page)
_MODULE_REDIRECTS = {
    "": "/hub/",
    "files": "/hub/",
    "hub": "/hub/",
    "console": "/console/workspace/",
    "writer": "/writer/",
    "scholar": "/scholar/",
    "vis": "/vis/editor/",
    "clew": "/clew/",
}

urlpatterns = [
    # Root /unified/ → hub
    path(
        "",
        RedirectView.as_view(url="/hub/", permanent=False),
        name="unified_index",
    ),
    # AJAX content endpoint (keep for backwards compat during transition)
    path("content/<str:module>/", unified_content, name="unified_content"),
    # Per-module redirects to native URLs
    path(
        "files/",
        RedirectView.as_view(url="/hub/", permanent=False),
        name="unified_files",
    ),
    path(
        "hub/",
        RedirectView.as_view(url="/hub/", permanent=False),
        name="unified_hub",
    ),
    path(
        "console/",
        RedirectView.as_view(url="/console/workspace/", permanent=False),
        name="unified_console",
    ),
    path(
        "writer/",
        RedirectView.as_view(url="/writer/", permanent=False),
        name="unified_writer",
    ),
    path(
        "scholar/",
        RedirectView.as_view(url="/scholar/", permanent=False),
        name="unified_scholar",
    ),
    path(
        "vis/",
        RedirectView.as_view(url="/vis/editor/", permanent=False),
        name="unified_vis",
    ),
    path(
        "clew/",
        RedirectView.as_view(url="/clew/", permanent=False),
        name="unified_clew",
    ),
    # Fallback for any unknown module — redirect to hub
    path(
        "<str:module>/",
        RedirectView.as_view(url="/hub/", permanent=False),
        name="unified_module",
    ),
]

# EOF
