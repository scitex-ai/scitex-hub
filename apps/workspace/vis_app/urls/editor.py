#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vis app URLs - Editor and plot rendering endpoints."""

from __future__ import annotations

from django.urls import path

from ..views import api as api_views

# Backend plot renderer (matplotlib/scitex.plt)
plot_patterns = [
    path("api/plot/", api_views.render_plot, name="api_render_plot"),
    path(
        "api/plot/gallery/",
        api_views.render_gallery_plot,
        name="api_render_gallery_plot",
    ),
    path(
        "api/upload-plot-data/", api_views.upload_plot_data, name="api_upload_plot_data"
    ),
    # Extract metadata from PNG images (for axis snap/align)
    path(
        "api/plot/metadata/",
        api_views.extract_image_metadata,
        name="api_extract_image_metadata",
    ),
]

# SciTeX Editor API endpoints
editor_patterns = [
    path("api/editor/load/", api_views.load_figure_json, name="api_editor_load"),
    path("api/editor/preview/", api_views.update_preview, name="api_editor_preview"),
    path("api/editor/save/", api_views.save_manual_overrides, name="api_editor_save"),
    path("api/editor/export/", api_views.export_figure, name="api_editor_export"),
    path("api/editor/style/", api_views.get_scitex_style, name="api_editor_style"),
]

urlpatterns = plot_patterns + editor_patterns


# EOF
