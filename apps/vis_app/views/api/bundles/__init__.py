"""
Bundle API Views Package.

Exports all bundle-related API views for pltz and figz operations.
"""

# PltzBundle CRUD API
# Bundle creation
from .create import (
    create_empty_figz,
    export_figz_bundle,
)

# Bundle downloads
from .download import (
    download_figz_bundle,
    download_figz_d_bundle,
    download_pltz_bundle,
    download_stx_bundle,
    export_figz_image,
)

# FigzBundle CRUD API
from .figz import (
    add_figz_panel,
    create_figz_bundle,
    delete_figz_bundle,
    get_figz_bundle,
    get_figz_panel_previews,
    get_figz_preview,
    get_layout_options,
    list_figz_bundles,
    remove_figz_panel,
    update_figz_bundle,
)

# Path-based API (for canvas integration)
from .path_api import (
    # Gallery -> Figz flow (no standalone pltz)
    add_panel_to_figz,
    create_pltz_from_plot,
    get_figz_panel_preview,
    get_pltz_data_by_path,
    get_pltz_geometry_by_path,
    get_pltz_preview_by_path,
    load_figz_by_path,
    load_pltz_by_path,
    render_pltz_by_path,
    save_figz_canvas,
    update_pltz_by_path,
)
from .pltz import (
    create_pltz_bundle,
    delete_pltz_bundle,
    get_pltz_bundle,
    get_pltz_data,
    get_pltz_geometry,
    get_pltz_preview,
    list_pltz_bundles,
    update_pltz_bundle,
)

__all__ = [
    # PltzBundle CRUD
    "list_pltz_bundles",
    "create_pltz_bundle",
    "get_pltz_bundle",
    "update_pltz_bundle",
    "delete_pltz_bundle",
    "get_pltz_preview",
    "get_pltz_data",
    "get_pltz_geometry",
    # FigzBundle CRUD
    "list_figz_bundles",
    "create_figz_bundle",
    "get_figz_bundle",
    "update_figz_bundle",
    "delete_figz_bundle",
    "get_figz_preview",
    "add_figz_panel",
    "remove_figz_panel",
    "get_figz_panel_previews",
    "get_layout_options",
    # Path-based API
    "load_figz_by_path",
    "load_pltz_by_path",
    "get_pltz_preview_by_path",
    "get_pltz_geometry_by_path",
    "get_pltz_data_by_path",
    "update_pltz_by_path",
    "render_pltz_by_path",
    "create_pltz_from_plot",
    "save_figz_canvas",
    # Gallery -> Figz flow (no standalone pltz)
    "add_panel_to_figz",
    "get_figz_panel_preview",
    # Bundle creation
    "create_empty_figz",
    "export_figz_bundle",
    # Bundle downloads
    "download_figz_bundle",
    "download_figz_d_bundle",
    "download_pltz_bundle",
    "download_stx_bundle",
    "export_figz_image",
]
