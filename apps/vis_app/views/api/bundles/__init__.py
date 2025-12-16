"""
Bundle API Views Package.

Exports all bundle-related API views for pltz and figz operations.
"""

# PltzBundle CRUD API
from .pltz import (
    list_pltz_bundles,
    create_pltz_bundle,
    get_pltz_bundle,
    update_pltz_bundle,
    delete_pltz_bundle,
    get_pltz_preview,
    get_pltz_data,
    get_pltz_geometry,
)

# FigzBundle CRUD API
from .figz import (
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
)

# Path-based API (for canvas integration)
from .path_api import (
    load_figz_by_path,
    load_pltz_by_path,
    get_pltz_preview_by_path,
    get_pltz_geometry_by_path,
    get_pltz_data_by_path,
    update_pltz_by_path,
    render_pltz_by_path,
    create_pltz_from_plot,
    save_figz_canvas,
)

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
    export_figz_image,
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
    # Bundle creation
    "create_empty_figz",
    "export_figz_bundle",
    # Bundle downloads
    "download_figz_bundle",
    "download_figz_d_bundle",
    "download_pltz_bundle",
    "export_figz_image",
]
