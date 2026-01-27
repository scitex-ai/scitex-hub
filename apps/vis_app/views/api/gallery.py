"""
Plot Type Gallery API - Serves plot templates and thumbnails from scitex examples.

Re-exports from specialized submodules:
- gallery_base: Basic gallery endpoints
- gallery_project: Project-based gallery endpoints
"""

# Re-export all gallery views for backward compatibility
from .gallery_base import (
    get_categories,
    get_plot_galleries,
    get_plot_template,
    get_plot_thumbnail,
)
from .gallery_project import (
    generate_project_gallery,
    get_plot_metadata,
    get_project_gallery,
    get_project_gallery_csv,
    get_project_gallery_image,
    list_gallery_categories_available,
)

__all__ = [
    # Base gallery
    "get_plot_galleries",
    "get_plot_thumbnail",
    "get_plot_template",
    "get_categories",
    # Project gallery
    "generate_project_gallery",
    "get_project_gallery",
    "get_project_gallery_image",
    "get_project_gallery_csv",
    "list_gallery_categories_available",
    "get_plot_metadata",
]
