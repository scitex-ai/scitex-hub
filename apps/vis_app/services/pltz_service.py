"""PltzBundle Service - Thin Django wrapper around scitex.plt.Pltz."""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

from django.conf import settings
from django.utils.text import slugify

logger = logging.getLogger(__name__)

SCITEX_CODE_PATH = os.environ.get(
    "SCITEX_CODE_PATH", "/home/ywatanabe/proj/scitex-code"
)
if SCITEX_CODE_PATH not in sys.path:
    sys.path.insert(0, f"{SCITEX_CODE_PATH}/src")


def _get_pltz_class():
    """Lazy import Pltz class."""
    from scitex.plt import Pltz

    return Pltz


class PltzService:
    """Thin service wrapper for pltz bundle operations."""

    @staticmethod
    def get_bundle_base_path(user_id: int) -> Path:
        """Get base path for user's pltz bundles."""
        return Path(settings.MEDIA_ROOT) / "vis" / "bundles" / "pltz" / str(user_id)

    @staticmethod
    def load_bundle(bundle_path: Union[str, Path]) -> Dict[str, Any]:
        """Load a pltz bundle using scitex.plt.Pltz."""
        Pltz = _get_pltz_class()
        path = Path(bundle_path)
        if not path.exists():
            raise FileNotFoundError(f"Bundle not found: {path}")
        pltz = Pltz(path)
        return {
            "path": str(path),
            "is_zip": path.suffix == ".pltz",
            "spec": pltz.spec,
            "style": pltz.style,
            "data": pltz.data,
        }

    @staticmethod
    def save_bundle(
        spec: Dict,
        style: Dict,
        data_csv: Optional[str] = None,
        output_path: Optional[Union[str, Path]] = None,
        user_id: Optional[int] = None,
        name: Optional[str] = None,
        as_zip: bool = True,
    ) -> Dict[str, Any]:
        """Save a new pltz bundle using scitex.plt.Pltz."""
        from io import StringIO

        import pandas as pd

        Pltz = _get_pltz_class()
        if output_path:
            path = Path(output_path)
        elif user_id and name:
            base_path = PltzService.get_bundle_base_path(user_id)
            base_path.mkdir(parents=True, exist_ok=True)
            path = base_path / f"{slugify(name)}.pltz"
        else:
            raise ValueError("Either output_path or (user_id, name) required")
        df = (
            pd.read_csv(data_csv if Path(data_csv).is_file() else StringIO(data_csv))
            if data_csv
            else None
        )
        plot_type = spec.get("plot_type", "line")
        pltz = Pltz.create(path, plot_type=plot_type, data=df, spec_overrides=spec)
        if style:
            pltz.style = style
            pltz.save()
        return {
            "path": str(path),
            "is_zip": True,
            "spec": pltz.spec,
            "style": pltz.style,
        }

    @staticmethod
    def update_spec(bundle_path: Union[str, Path], spec: Dict) -> Dict[str, Any]:
        """Update spec.json in bundle."""
        pltz = _get_pltz_class()(bundle_path)
        pltz.spec = spec
        pltz.save()
        return {"path": str(bundle_path), "spec": spec}

    @staticmethod
    def update_style(bundle_path: Union[str, Path], style: Dict) -> Dict[str, Any]:
        """Update style.json in bundle."""
        pltz = _get_pltz_class()(bundle_path)
        pltz.style = style
        pltz.save()
        return {"path": str(bundle_path), "style": style}

    @staticmethod
    def get_data_csv(bundle_path: Union[str, Path]) -> Optional[str]:
        """Get data CSV content from bundle. Handles pltz inside figz bundles."""
        path_str = str(bundle_path)

        # Handle pltz embedded in figz (path like "Figure1.figz/A.pltz")
        if ".figz/" in path_str:
            from scitex.fig import Figz

            figz_path, panel_pltz = path_str.split(".figz/", 1)
            figz = Figz(figz_path + ".figz")
            panel_id = panel_pltz.replace(".pltz", "")
            data = figz.get_panel_data(panel_id)
            if data is not None:
                return data.to_csv(index=False)
            return None

        # Standard standalone pltz
        try:
            pltz = _get_pltz_class()(bundle_path)
            if pltz.data is not None:
                return pltz.data.to_csv(index=False)
        except Exception as e:
            logger.warning(f"Failed to get data: {e}")
        return None

    @staticmethod
    def get_geometry(bundle_path: Union[str, Path]) -> Optional[Dict]:
        """Get geometry cache from bundle."""
        from scitex.io.bundle import ZipBundle

        try:
            with ZipBundle(bundle_path, mode="r") as zb:
                return zb.read_json("cache/geometry_px.json")
        except (FileNotFoundError, Exception):
            return None

    @staticmethod
    def delete_bundle(bundle_path: Union[str, Path]) -> bool:
        """Delete a pltz bundle."""
        import shutil

        path = Path(bundle_path)
        if not path.exists():
            return False
        path.unlink() if path.is_file() else shutil.rmtree(path)
        return True

    @staticmethod
    def is_pltz_bundle(path: Union[str, Path]) -> bool:
        """Check if path is a valid pltz bundle."""
        path = Path(path)
        if path.suffix == ".pltz" and path.is_file():
            from scitex.io.bundle import ZipBundle

            try:
                with ZipBundle(path, mode="r") as zb:
                    zb.read_json("spec.json")
                return True
            except Exception:
                return False
        return False

    # Delegate to specialized services
    @staticmethod
    def get_preview_image(
        bundle_path: Union[str, Path], image_type: str = "png"
    ) -> Optional[bytes]:
        """Get preview image (delegates to PltzPreviewService)."""
        from .pltz_preview_service import PltzPreviewService

        return PltzPreviewService.get_preview_image(bundle_path, image_type)

    @staticmethod
    def render_preview(bundle_path: Union[str, Path]) -> Dict[str, Any]:
        """Re-render preview (delegates to PltzPreviewService)."""
        from .pltz_preview_service import PltzPreviewService

        return PltzPreviewService.render_preview(bundle_path)

    @staticmethod
    def get_preview_base64(
        bundle_path: Union[str, Path], image_type: str = "png"
    ) -> Optional[str]:
        """Get preview as base64 (delegates to PltzPreviewService)."""
        from .pltz_preview_service import PltzPreviewService

        return PltzPreviewService.get_preview_base64(bundle_path, image_type)

    @staticmethod
    def categorize_plot(spec: Dict) -> str:
        """Categorize plot (delegates to PltzCreationService)."""
        from .pltz_creation_service import PltzCreationService

        return PltzCreationService.categorize_plot(spec)

    @staticmethod
    def create_from_gallery(
        gallery_category: str,
        gallery_plot_name: str,
        output_path: Union[str, Path],
        project_owner: Optional[str] = None,
        project_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create from gallery (delegates to PltzCreationService)."""
        from .pltz_creation_service import PltzCreationService

        return PltzCreationService.create_from_gallery(
            gallery_category,
            gallery_plot_name,
            output_path,
            project_owner,
            project_slug,
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
    ) -> Dict[str, Any]:
        """Create from plot (delegates to PltzCreationService)."""
        from .pltz_creation_service import PltzCreationService

        return PltzCreationService.create_from_plot(
            plot_type=plot_type,
            data_csv=data_csv,
            data=data,
            name=name,
            output_dir=output_dir,
            project_owner=project_owner,
            project_slug=project_slug,
            figure_name=figure_name,
            panel_label=panel_label,
            user=user,
            gallery_category=gallery_category,
            gallery_plot_name=gallery_plot_name,
            bundle_base_path_fn=PltzService.get_bundle_base_path,
        )
