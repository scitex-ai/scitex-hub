from django.urls import path

from . import views
from .views import api as api_views

app_name = "vis"

urlpatterns = [
    # Main editor - Vis (VisPlot-inspired, now default)
    path(
        "",
        views.figure_editor,
        name="figure_editor",
    ),
    # Gallery page - shows all available plot types
    path(
        "gallery/",
        views.gallery_page,
        name="gallery",
    ),
    # Legacy canvas-based editor
    path(
        "legacy/",
        views.figure_editor_legacy,
        name="figure_editor_legacy",
    ),
    # Figure management
    path(
        "figures/",
        views.figure_list,
        name="figure_list",
    ),
    path(
        "figures/create/",
        views.create_figure,
        name="create_figure",
    ),
    path(
        "figures/<uuid:figure_id>/",
        views.figure_detail,
        name="figure_detail",
    ),
    # API endpoints
    path(
        "api/presets/",
        api_views.get_journal_presets,
        name="api_presets",
    ),
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
    # Version management endpoints (Original | Edited Cards)
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
    # Image conversion
    path(
        "api/convert/png-to-tiff/",
        api_views.convert_png_to_tiff,
        name="api_convert_png_to_tiff",
    ),
    # Backend plot renderer (matplotlib/scitex.plt)
    path(
        "api/plot/",
        api_views.render_plot,
        name="api_render_plot",
    ),
    path(
        "api/plot/gallery/",
        api_views.render_gallery_plot,
        name="api_render_gallery_plot",
    ),
    path(
        "api/upload-plot-data/",
        api_views.upload_plot_data,
        name="api_upload_plot_data",
    ),
    # Extract metadata from PNG images (for axis snap/align)
    path(
        "api/plot/metadata/",
        api_views.extract_image_metadata,
        name="api_extract_image_metadata",
    ),
    # SciTeX Editor API endpoints
    path(
        "api/editor/load/",
        api_views.load_figure_json,
        name="api_editor_load",
    ),
    path(
        "api/editor/preview/",
        api_views.update_preview,
        name="api_editor_preview",
    ),
    path(
        "api/editor/save/",
        api_views.save_manual_overrides,
        name="api_editor_save",
    ),
    path(
        "api/editor/export/",
        api_views.export_figure,
        name="api_editor_export",
    ),
    path(
        "api/editor/style/",
        api_views.get_scitex_style,
        name="api_editor_style",
    ),
    # =========================================================================
    # Style Preset API endpoints
    # =========================================================================
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
    # Gallery API endpoints (plot type thumbnails)
    path(
        "api/gallery/",
        api_views.get_plot_galleries,
        name="api_gallery",
    ),
    path(
        "api/gallery/categories/",
        api_views.get_categories,
        name="api_gallery_categories",
    ),
    path(
        "api/gallery/<str:gallery_id>/<str:plot_id>/thumbnail/",
        api_views.get_plot_thumbnail,
        name="api_gallery_thumbnail",
    ),
    path(
        "api/gallery/<str:gallery_id>/<str:plot_id>/template/",
        api_views.get_plot_template,
        name="api_gallery_template",
    ),
    # Project-based gallery endpoints
    path(
        "api/gallery/generate/",
        api_views.generate_project_gallery,
        name="api_gallery_generate",
    ),
    path(
        "api/gallery/project/",
        api_views.get_project_gallery,
        name="api_gallery_project",
    ),
    path(
        "api/gallery/project/<str:category>/<str:plot_name>/image/",
        api_views.get_project_gallery_image,
        name="api_gallery_project_image",
    ),
    path(
        "api/gallery/project/<str:category>/<str:plot_name>/csv/",
        api_views.get_project_gallery_csv,
        name="api_gallery_project_csv",
    ),
    path(
        "api/gallery/available/",
        api_views.list_gallery_categories_available,
        name="api_gallery_available",
    ),
    # Axis metadata for snap/align by axis position
    path(
        "api/gallery/metadata/<str:category>/<str:plot_name>/",
        api_views.get_plot_metadata,
        name="api_gallery_metadata",
    ),
    # =========================================================================
    # Statistics API endpoints (scitex.stats integration)
    # =========================================================================
    # Get applicable tests for right-click context menu
    path(
        "api/stats/applicable/",
        api_views.get_applicable_tests,
        name="api_stats_applicable",
    ),
    # Run a specific statistical test
    path(
        "api/stats/run/",
        api_views.run_statistical_test,
        name="api_stats_run",
    ),
    # Run all applicable tests (magic mode)
    path(
        "api/stats/run-all/",
        api_views.run_all_applicable,
        name="api_stats_run_all",
    ),
    # Build StatContext from plot metadata
    path(
        "api/stats/context/",
        api_views.build_context_from_plot,
        name="api_stats_context",
    ),
    # =========================================================================
    # PltzBundle API endpoints (.pltz plot bundles)
    # =========================================================================
    path(
        "api/bundles/pltz/",
        api_views.list_pltz_bundles,
        name="api_pltz_list",
    ),
    path(
        "api/bundles/pltz/create/",
        api_views.create_pltz_bundle,
        name="api_pltz_create",
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
    # =========================================================================
    # FigzBundle API endpoints (.figz figure bundles)
    # =========================================================================
    path(
        "api/bundles/figz/",
        api_views.list_figz_bundles,
        name="api_figz_list",
    ),
    path(
        "api/bundles/figz/create/",
        api_views.create_figz_bundle,
        name="api_figz_create",
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
    # =========================================================================
    # Path-Based Bundle API endpoints (for canvas integration)
    # =========================================================================
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
    # =========================================================================
    # Gallery → Canvas → Bundle Flow (auto-save system)
    # =========================================================================
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
        "api/bundles/figz/export/",
        api_views.export_figz_bundle,
        name="api_figz_export",
    ),
    # =========================================================================
    # Download Bundle Endpoints (GET-based for direct download)
    # =========================================================================
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
    # =========================================================================
    # Unified .stx Bundle Download (supports .stx, .figz, .pltz)
    # =========================================================================
    path(
        "api/bundles/stx/download/",
        api_views.download_stx_bundle,
        name="api_stx_download",
    ),
]
