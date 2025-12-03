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
    upload_plot_data,
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
    'upload_plot_data',
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
]
