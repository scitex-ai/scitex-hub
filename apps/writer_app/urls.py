#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04 20:46:56 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/urls.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/writer_app/urls.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------
"""
Writer App URLs - Feature-based organization.

This file serves as the main entry point for writer_app URLs,
delegating to feature-based URL modules following FULLSTACK.md guidelines.

The URL structure is organized by feature domains:
- Index: Main entry points and workspace management
- Editor: Document editing and section management
- Compilation: LaTeX compilation and PDF generation
- Version Control: Git-based version management
- arXiv: arXiv submission and integration
- Collaboration: Real-time collaborative editing
- Overleaf: Overleaf import/export integration

All routes are defined in their respective feature modules under urls/
"""

from django.urls import include, path

app_name = "writer_app"

urlpatterns = [
    # Main writer page (simple editor with PDF viewer)
    path("", include("apps.writer_app.urls.index")),
    # API endpoints for editor operations
    path("api/", include("apps.writer_app.urls.api")),
    path("editor/", include("apps.writer_app.urls.editor")),
    path("compilation/", include("apps.writer_app.urls.compilation")),
    path("collaboration/", include("apps.writer_app.urls.collaboration")),
    # Overleaf import/export
    path("overleaf/", include("apps.writer_app.urls.overleaf")),
]

# EOF
