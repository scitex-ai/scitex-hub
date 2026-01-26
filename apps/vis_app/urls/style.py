#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vis app URLs - Style preset endpoints."""

from __future__ import annotations

from django.urls import path

from ..views import api as api_views

# Style Preset API endpoints
urlpatterns = [
    path(
        "api/style-presets/",
        api_views.list_style_presets,
        name="api_style_presets_list",
    ),
    path(
        "api/style-presets/create/",
        api_views.create_style_preset,
        name="api_style_presets_create",
    ),
    path(
        "api/style-presets/active/",
        api_views.get_active_style,
        name="api_style_presets_active",
    ),
    path(
        "api/style-presets/import/",
        api_views.import_preset_yaml,
        name="api_style_presets_import",
    ),
    path(
        "api/style-presets/<uuid:preset_id>/",
        api_views.get_style_preset,
        name="api_style_presets_detail",
    ),
    path(
        "api/style-presets/<uuid:preset_id>/update/",
        api_views.update_style_preset,
        name="api_style_presets_update",
    ),
    path(
        "api/style-presets/<uuid:preset_id>/delete/",
        api_views.delete_style_preset,
        name="api_style_presets_delete",
    ),
    path(
        "api/style-presets/<uuid:preset_id>/activate/",
        api_views.activate_style_preset,
        name="api_style_presets_activate",
    ),
    path(
        "api/style-presets/<uuid:preset_id>/export/",
        api_views.export_preset_yaml,
        name="api_style_presets_export",
    ),
]


# EOF
