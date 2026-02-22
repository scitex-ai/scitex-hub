"""PltzBundle Creation Service - Gallery and plot creation operations."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class PltzCreationService:
    """Service for creating pltz bundles from gallery templates."""

    @staticmethod
    def categorize_plot(spec: Dict) -> str:
        """Determine plot category from spec."""
        plot_type = spec.get("plot_type", "").lower()
        categories = {
            "line": ["line", "step", "stem"],
            "scatter": ["scatter"],
            "bar": ["bar", "barh"],
            "distribution": ["histogram", "kde", "ecdf"],
            "statistical": ["boxplot", "violinplot"],
            "heatmap": ["heatmap", "imshow", "contour"],
        }
        return next(
            (cat for cat, types in categories.items() if plot_type in types), "other"
        )

    @staticmethod
    def create_from_gallery(
        gallery_category: str,
        gallery_plot_name: str,
        output_path: Union[str, Path],
        project_owner: Optional[str] = None,
        project_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create pltz bundle from gallery template.

        Note: Creating a standalone .plt.zip from a gallery template requires
        a recorded figrecipe figure. Use PlotsService.render_gallery_plot()
        to render panels as PNG images, or record a new figure with figrecipe.subplots().
        """
        raise NotImplementedError(
            "create_from_gallery is not implemented. "
            "Use PlotsService.render_gallery_plot() to render gallery panels as images, "
            "or record a figure with figrecipe.subplots() + figrecipe.save_bundle()."
        )

    @staticmethod
    def create_from_plot(
        plot_type: str,
        data_csv: Optional[str] = None,
        data: Optional[Any] = None,
        name: Optional[str] = None,
        output_dir: Optional[str] = None,
        project_owner: Optional[str] = None,
        project_slug: Optional[str] = None,
        figure_name: Optional[str] = None,
        panel_label: Optional[str] = None,
        user: Optional[Any] = None,
        gallery_category: Optional[str] = None,
        gallery_plot_name: Optional[str] = None,
        bundle_base_path_fn=None,
    ) -> Dict[str, Any]:
        """Create pltz bundle from gallery template, optionally with user data."""
        if not gallery_category or not gallery_plot_name:
            raise ValueError("gallery_category and gallery_plot_name required")
        return PltzCreationService.create_from_gallery(
            gallery_category,
            gallery_plot_name,
            output_dir or ".",
            project_owner,
            project_slug,
        )
