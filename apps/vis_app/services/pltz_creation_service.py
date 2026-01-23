"""PltzBundle Creation Service - Gallery and plot creation operations."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


def _get_pltz_class():
    """Lazy import Pltz class."""
    from scitex.plt import Pltz

    return Pltz


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
        """Create pltz bundle from gallery template."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pltz = _get_pltz_class().create_from_gallery(
            path, gallery_category, gallery_plot_name
        )
        return {"bundle_path": str(path), "spec": pltz.spec, "style": pltz.style}

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
        bundle_name = panel_label or name or "plot"
        if output_dir:
            bundle_path = Path(output_dir) / f"{bundle_name}.pltz"
            bundle_path.parent.mkdir(parents=True, exist_ok=True)
        elif project_owner and project_slug:
            from apps.project_app.models import Project

            project = Project.objects.get(
                owner__username=project_owner, slug=project_slug
            )
            figures_dir = project.get_local_path() / "scitex" / "vis" / "figures"
            figures_dir.mkdir(parents=True, exist_ok=True)
            bundle_path = figures_dir / f"{bundle_name}.pltz"
        elif user and bundle_base_path_fn:
            base_path = bundle_base_path_fn(user.id)
            base_path.mkdir(parents=True, exist_ok=True)
            bundle_path = base_path / f"{bundle_name}.pltz"
        else:
            raise ValueError("output_dir, project info, or user required")
        result = PltzCreationService.create_from_gallery(
            gallery_category, gallery_plot_name, bundle_path
        )
        if data_csv:
            from io import StringIO

            import pandas as pd

            pltz = _get_pltz_class()(bundle_path)
            pltz.data = pd.read_csv(StringIO(data_csv))
            pltz.save()
            result["data_updated"] = True
        return result
