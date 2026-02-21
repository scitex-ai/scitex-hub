"""PltzBundle Service - Thin Django wrapper around figrecipe bundle functions."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from django.conf import settings

logger = logging.getLogger(__name__)


class PltzService:
    """Thin service wrapper for pltz bundle operations."""

    @staticmethod
    def get_bundle_base_path(user_id: int) -> Path:
        """Get base path for user's pltz bundles."""
        return Path(settings.MEDIA_ROOT) / "vis" / "bundles" / "pltz" / str(user_id)

    @staticmethod
    def load_bundle(bundle_path: Union[str, Path]) -> Dict[str, Any]:
        """Load a pltz bundle using figrecipe.load_bundle."""
        import figrecipe

        path = Path(bundle_path)
        if not path.exists():
            raise FileNotFoundError(f"Bundle not found: {path}")
        spec, style, data = figrecipe.load_bundle(path)
        return {
            "path": str(path),
            "is_zip": True,
            "spec": spec,
            "style": style,
            "data": data,
        }

    @staticmethod
    def update_spec(bundle_path: Union[str, Path], spec: Dict) -> Dict[str, Any]:
        """Update spec.json in bundle."""
        import figrecipe

        pltz = figrecipe.Pltz(bundle_path)
        pltz.spec = spec
        pltz.save()
        return {"path": str(bundle_path), "spec": spec}

    @staticmethod
    def update_style(bundle_path: Union[str, Path], style: Dict) -> Dict[str, Any]:
        """Update style.json in bundle."""
        import figrecipe

        pltz = figrecipe.Pltz(bundle_path)
        pltz.style = style
        pltz.save()
        return {"path": str(bundle_path), "style": style}

    @staticmethod
    def get_data_csv(bundle_path: Union[str, Path]) -> Optional[str]:
        """Get data CSV content from bundle. Handles pltz inside figz bundles."""
        import figrecipe

        path_str = str(bundle_path)

        # Handle pltz embedded in figz (path like "Figure1.figz/A.pltz")
        if ".figz/" in path_str:
            figz_path_str, panel_part = path_str.split(".figz/", 1)
            figz = figrecipe.Figz(Path(figz_path_str + ".figz"))
            panel_id = panel_part.replace(".pltz", "").replace(".plt.zip", "")
            data = figz.get_panel_data(panel_id)
            if data is not None:
                return data.to_csv(index=False)
            return None

        # Standard standalone pltz
        try:
            _, _, data = figrecipe.load_bundle(bundle_path)
            if data is not None:
                return data.to_csv(index=False)
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
        except Exception:
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
        if path.suffix in (".pltz", ".zip") and path.is_file():
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
