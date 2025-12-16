"""
Scientific Figure Editor - API Views Module
Modular REST API endpoints for the Canvas editor

This module provides backward compatibility by re-exporting all API views
from their respective modules.
"""

# Journal Preset Views
from .presets import (
    get_journal_presets,
    get_preset_detail,
)

# Figure State Management Views
from .figures import (
    save_figure_state,
    load_figure_state,
    upload_panel_image,
    update_figure_config,
)

# Version Management Views
from .versions import (
    create_version_snapshot,
    get_figure_versions,
    load_version_state,
    set_original_version,
    get_original_version,
)

# Image Conversion Views
from .conversion import (
    convert_png_to_tiff,
)

# Plot Rendering Views
from .plots import (
    render_plot,
    render_gallery_plot,
    upload_plot_data,
    extract_image_metadata,
)

# SciTeX Editor Views
from .scitex_editor import (
    load_figure_json,
    update_preview,
    save_manual_overrides,
    export_figure,
)

# Gallery Views
from .gallery import (
    get_plot_galleries,
    get_plot_thumbnail,
    get_plot_template,
    get_categories,
    # Project-based gallery
    generate_project_gallery,
    get_project_gallery,
    get_project_gallery_image,
    get_project_gallery_csv,
    list_gallery_categories_available,
    # Axis metadata for snap/align
    get_plot_metadata,
)

# Statistics Views
from .stats import (
    get_applicable_tests,
    run_statistical_test,
    run_all_applicable,
    build_context_from_plot,
)

# Bundle Views (pltz/figz)
from .bundles import (
    # PltzBundle endpoints
    list_pltz_bundles,
    create_pltz_bundle,
    get_pltz_bundle,
    update_pltz_bundle,
    delete_pltz_bundle,
    get_pltz_preview,
    get_pltz_data,
    get_pltz_geometry,
    # FigzBundle endpoints
    list_figz_bundles,
    create_figz_bundle,
    get_figz_bundle,
    update_figz_bundle,
    delete_figz_bundle,
    get_figz_preview,
    add_figz_panel,
    remove_figz_panel,
    get_figz_panel_previews,
    get_layout_options,
    # Path-based bundle endpoints (for canvas integration)
    load_figz_by_path,
    load_pltz_by_path,
    get_pltz_preview_by_path,
    get_pltz_geometry_by_path,
    get_pltz_data_by_path,
    update_pltz_by_path,
    render_pltz_by_path,
    # Gallery → Canvas → Bundle flow (auto-save system)
    create_pltz_from_plot,
    save_figz_canvas,
    export_figz_bundle,
    # Download endpoints
    download_figz_bundle,
    download_figz_d_bundle,
    download_pltz_bundle,
    export_figz_image,
    # Create empty figz bundle
    create_empty_figz,
)

__all__ = [
    # Presets
    'get_journal_presets',
    'get_preset_detail',
    # Figures
    'save_figure_state',
    'load_figure_state',
    'upload_panel_image',
    'update_figure_config',
    # Versions
    'create_version_snapshot',
    'get_figure_versions',
    'load_version_state',
    'set_original_version',
    'get_original_version',
    # Conversion
    'convert_png_to_tiff',
    # Plots
    'render_plot',
    'render_gallery_plot',
    'upload_plot_data',
    'extract_image_metadata',
    # SciTeX Editor
    'load_figure_json',
    'update_preview',
    'save_manual_overrides',
    'export_figure',
    # Gallery
    'get_plot_galleries',
    'get_plot_thumbnail',
    'get_plot_template',
    'get_categories',
    # Project-based gallery
    'generate_project_gallery',
    'get_project_gallery',
    'get_project_gallery_image',
    'get_project_gallery_csv',
    'list_gallery_categories_available',
    # Axis metadata for snap/align
    'get_plot_metadata',
    # Statistics
    'get_applicable_tests',
    'run_statistical_test',
    'run_all_applicable',
    'build_context_from_plot',
    # Bundles (pltz/figz)
    'list_pltz_bundles',
    'create_pltz_bundle',
    'get_pltz_bundle',
    'update_pltz_bundle',
    'delete_pltz_bundle',
    'get_pltz_preview',
    'get_pltz_data',
    'get_pltz_geometry',
    'list_figz_bundles',
    'create_figz_bundle',
    'get_figz_bundle',
    'update_figz_bundle',
    'delete_figz_bundle',
    'get_figz_preview',
    'add_figz_panel',
    'remove_figz_panel',
    'get_figz_panel_previews',
    'get_layout_options',
    # Path-based bundle endpoints
    'load_figz_by_path',
    'load_pltz_by_path',
    'get_pltz_preview_by_path',
    'get_pltz_geometry_by_path',
    'get_pltz_data_by_path',
    'update_pltz_by_path',
    'render_pltz_by_path',
    # Gallery → Canvas → Bundle flow
    'create_pltz_from_plot',
    'save_figz_canvas',
    'export_figz_bundle',
    # Download endpoints
    'download_figz_bundle',
    'download_figz_d_bundle',
    'download_pltz_bundle',
    'export_figz_image',
    # Create empty figz bundle
    'create_empty_figz',
]
