#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vis app URLs - Figure API and version management endpoints."""

from __future__ import annotations

from django.urls import path

from ..views import api as api_views

# Basic figure API endpoints
figure_api_patterns = [
    path("api/presets/", api_views.get_journal_presets, name="api_presets"),
    path(
        "api/presets/<int:preset_id>/",
        api_views.get_preset_detail,
        name="api_preset_detail",
    ),
    path(
        "api/figures/<uuid:figure_id>/save/",
        api_views.save_figure_state,
        name="api_save_figure",
    ),
    path(
        "api/figures/<uuid:figure_id>/load/",
        api_views.load_figure_state,
        name="api_load_figure",
    ),
    path(
        "api/figures/<uuid:figure_id>/upload-panel/",
        api_views.upload_panel_image,
        name="api_upload_panel",
    ),
    path(
        "api/figures/<uuid:figure_id>/config/",
        api_views.update_figure_config,
        name="api_update_config",
    ),
]

# Version management endpoints (Original | Edited Cards)
version_patterns = [
    path(
        "api/figures/<uuid:figure_id>/versions/",
        api_views.get_figure_versions,
        name="api_get_versions",
    ),
    path(
        "api/figures/<uuid:figure_id>/versions/create/",
        api_views.create_version_snapshot,
        name="api_create_version",
    ),
    path(
        "api/figures/<uuid:figure_id>/versions/<uuid:version_id>/",
        api_views.load_version_state,
        name="api_load_version",
    ),
    path(
        "api/figures/<uuid:figure_id>/versions/original/set/",
        api_views.set_original_version,
        name="api_set_original",
    ),
    path(
        "api/figures/<uuid:figure_id>/versions/original/",
        api_views.get_original_version,
        name="api_get_original",
    ),
]

# Image conversion
conversion_patterns = [
    path(
        "api/convert/png-to-tiff/",
        api_views.convert_png_to_tiff,
        name="api_convert_png_to_tiff",
    ),
]

urlpatterns = figure_api_patterns + version_patterns + conversion_patterns


# EOF
