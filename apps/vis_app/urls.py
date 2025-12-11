from django.urls import path
from . import views
from .views import api as api_views

app_name = "vis"

urlpatterns = [
    # Main editor - Sigma (SigmaPlot-inspired, now default)
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
]
