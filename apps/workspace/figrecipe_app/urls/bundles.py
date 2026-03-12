#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vis app URLs - Bundle API endpoints (.pltz, .figz, .stx bundles)."""

from __future__ import annotations

from django.urls import path

from ..views import api as api_views

# PltzBundle API endpoints (.pltz plot bundles)
pltz_patterns = [
    path("api/bundles/pltz/", api_views.list_pltz_bundles, name="api_pltz_list"),
    path(
        "api/bundles/pltz/create/", api_views.create_pltz_bundle, name="api_pltz_create"
    ),
    path(
        "api/bundles/pltz/<uuid:bundle_id>/",
        api_views.get_pltz_bundle,
        name="api_pltz_detail",
    ),
    path(
        "api/bundles/pltz/<uuid:bundle_id>/update/",
        api_views.update_pltz_bundle,
        name="api_pltz_update",
    ),
    path(
        "api/bundles/pltz/<uuid:bundle_id>/delete/",
        api_views.delete_pltz_bundle,
        name="api_pltz_delete",
    ),
    path(
        "api/bundles/pltz/<uuid:bundle_id>/preview/",
        api_views.get_pltz_preview,
        name="api_pltz_preview",
    ),
    path(
        "api/bundles/pltz/<uuid:bundle_id>/data/",
        api_views.get_pltz_data,
        name="api_pltz_data",
    ),
    path(
        "api/bundles/pltz/<uuid:bundle_id>/geometry/",
        api_views.get_pltz_geometry,
        name="api_pltz_geometry",
    ),
]

# FigzBundle API endpoints (.figz figure bundles)
figz_patterns = [
    path("api/bundles/figz/", api_views.list_figz_bundles, name="api_figz_list"),
    path(
        "api/bundles/figz/create/", api_views.create_figz_bundle, name="api_figz_create"
    ),
    path(
        "api/bundles/figz/layouts/",
        api_views.get_layout_options,
        name="api_figz_layouts",
    ),
    path(
        "api/bundles/figz/<uuid:bundle_id>/",
        api_views.get_figz_bundle,
        name="api_figz_detail",
    ),
    path(
        "api/bundles/figz/<uuid:bundle_id>/update/",
        api_views.update_figz_bundle,
        name="api_figz_update",
    ),
    path(
        "api/bundles/figz/<uuid:bundle_id>/delete/",
        api_views.delete_figz_bundle,
        name="api_figz_delete",
    ),
    path(
        "api/bundles/figz/<uuid:bundle_id>/preview/",
        api_views.get_figz_preview,
        name="api_figz_preview",
    ),
    path(
        "api/bundles/figz/<uuid:bundle_id>/panels/",
        api_views.get_figz_panel_previews,
        name="api_figz_panels",
    ),
    path(
        "api/bundles/figz/<uuid:bundle_id>/panels/add/",
        api_views.add_figz_panel,
        name="api_figz_panel_add",
    ),
    path(
        "api/bundles/figz/<uuid:bundle_id>/panels/<str:label>/remove/",
        api_views.remove_figz_panel,
        name="api_figz_panel_remove",
    ),
]

# Path-Based Bundle API endpoints (for canvas integration)
path_based_patterns = [
    path(
        "api/bundles/figz/load/",
        api_views.load_figz_by_path,
        name="api_figz_load_by_path",
    ),
    path(
        "api/bundles/pltz/load/",
        api_views.load_pltz_by_path,
        name="api_pltz_load_by_path",
    ),
    path(
        "api/bundles/pltz/preview/",
        api_views.get_pltz_preview_by_path,
        name="api_pltz_preview_by_path",
    ),
    path(
        "api/bundles/pltz/geometry/",
        api_views.get_pltz_geometry_by_path,
        name="api_pltz_geometry_by_path",
    ),
    path(
        "api/bundles/pltz/data/",
        api_views.get_pltz_data_by_path,
        name="api_pltz_data_by_path",
    ),
    path(
        "api/bundles/pltz/update/",
        api_views.update_pltz_by_path,
        name="api_pltz_update_by_path",
    ),
    path(
        "api/bundles/pltz/render/",
        api_views.render_pltz_by_path,
        name="api_pltz_render_by_path",
    ),
    # Property update endpoints (fine-grained updates)
    path(
        "api/bundles/pltz/update-property/",
        api_views.update_pltz_property,
        name="api_pltz_update_property",
    ),
    path(
        "api/bundles/pltz/batch-update-properties/",
        api_views.batch_update_pltz_properties,
        name="api_pltz_batch_update_properties",
    ),
]

# Gallery → Canvas → Bundle Flow (auto-save system)
flow_patterns = [
    path(
        "api/bundles/pltz/create-from-plot/",
        api_views.create_pltz_from_plot,
        name="api_pltz_create_from_plot",
    ),
    path(
        "api/bundles/figz/save-canvas/",
        api_views.save_figz_canvas,
        name="api_figz_save_canvas",
    ),
    # Gallery -> Figz flow (no standalone pltz)
    path(
        "api/bundles/figz/add-panel/",
        api_views.add_panel_to_figz,
        name="api_figz_add_panel_by_path",
    ),
    path(
        "api/bundles/figz/panel-preview/",
        api_views.get_figz_panel_preview,
        name="api_figz_panel_preview_by_path",
    ),
    path(
        "api/bundles/figz/create-empty/",
        api_views.create_empty_figz,
        name="api_figz_create_empty",
    ),
    path(
        "api/bundles/figz/export/", api_views.export_figz_bundle, name="api_figz_export"
    ),
    # Project file content (CSV, TSV, TXT by filesystem path)
    path(
        "api/bundles/project-file/",
        api_views.get_project_file_content,
        name="api_project_file_content",
    ),
]

# Download Bundle Endpoints (GET-based for direct download)
download_patterns = [
    path(
        "api/bundles/figz/download/",
        api_views.download_figz_bundle,
        name="api_figz_download",
    ),
    path(
        "api/bundles/figz-d/download/",
        api_views.download_figz_d_bundle,
        name="api_figz_d_download",
    ),
    path(
        "api/bundles/pltz/download/",
        api_views.download_pltz_bundle,
        name="api_pltz_download",
    ),
    path(
        "api/bundles/figz/export-image/",
        api_views.export_figz_image,
        name="api_figz_export_image",
    ),
    # Unified .stx Bundle Download (supports .stx, .figz, .pltz)
    path(
        "api/bundles/stx/download/",
        api_views.download_stx_bundle,
        name="api_stx_download",
    ),
]

urlpatterns = (
    pltz_patterns
    + figz_patterns
    + path_based_patterns
    + flow_patterns
    + download_patterns
)


# EOF
