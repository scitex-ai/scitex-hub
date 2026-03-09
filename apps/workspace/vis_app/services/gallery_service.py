"""
Gallery Service - Business logic for plot gallery operations.

This module re-exports from specialized submodules for backward compatibility:
- gallery_core: Basic scanning and plot operations
- gallery_metadata: Template/metadata loading and categorization
- gallery_pltz: Pltz bundle integration
"""

from .gallery_core import EXAMPLES_PATH, SCITEX_CODE_PATH, GalleryCore
from .gallery_metadata import GalleryMetadata
from .gallery_pltz import GalleryPltz


class GalleryService:
    """Service for gallery-related operations (delegates to specialized classes)."""

    # Core operations
    get_plot_galleries = staticmethod(GalleryCore.get_plot_galleries)
    _scan_gallery = staticmethod(GalleryCore._scan_gallery)
    _categorize_plot = staticmethod(GalleryCore._categorize_plot)
    find_plot_in_galleries = staticmethod(GalleryCore.find_plot_in_galleries)
    load_thumbnail = staticmethod(GalleryCore.load_thumbnail)
    encode_thumbnail_base64 = staticmethod(GalleryCore.encode_thumbnail_base64)

    # Metadata operations
    load_plot_template = staticmethod(GalleryMetadata.load_plot_template)
    generate_boilerplate = staticmethod(GalleryMetadata.generate_boilerplate)
    format_categories = staticmethod(GalleryMetadata.format_categories)
    load_plot_metadata = staticmethod(GalleryMetadata.load_plot_metadata)
    _extract_metadata_fields = staticmethod(GalleryMetadata._extract_metadata_fields)

    # Pltz operations
    get_pltz_galleries = staticmethod(GalleryPltz.get_pltz_galleries)
    _scan_pltz_gallery = staticmethod(GalleryPltz._scan_pltz_gallery)
    load_pltz_from_gallery = staticmethod(GalleryPltz.load_pltz_from_gallery)
    get_pltz_preview_base64 = staticmethod(GalleryPltz.get_pltz_preview_base64)
    convert_legacy_to_pltz = staticmethod(GalleryPltz.convert_legacy_to_pltz)

    @staticmethod
    def get_category_counts():
        """Count plots by category across all galleries."""
        galleries = GalleryCore.get_plot_galleries()
        return GalleryMetadata.get_category_counts(galleries)


__all__ = [
    "GalleryService",
    "GalleryCore",
    "GalleryMetadata",
    "GalleryPltz",
    "SCITEX_CODE_PATH",
    "EXAMPLES_PATH",
]
