#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04 20:53:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/urls/index.py
# ----------------------------------------
"""Writer App Index URLs

Main index page and workspace initialization endpoints.
"""

from django.urls import path
from django.views.generic import TemplateView

from ..views.index import main as index_views
from ..views.index.debug import test_pdf

urlpatterns = [
    # Main index page
    path("", index_views.index_view, name="index"),
    # Workspace initialization
    path(
        "initialize-workspace/",
        index_views.initialize_workspace,
        name="initialize_workspace",
    ),
    # PDF rendering debug
    path(
        "pdf-debug/",
        TemplateView.as_view(template_name="writer_app/pdf_debug.html"),
        name="pdf_debug",
    ),
    path("pdf-debug/test.pdf", test_pdf, name="pdf_debug_test_pdf"),
]

# EOF
