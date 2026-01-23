"""PltzBundle Preview Service - Preview and rendering operations."""

import logging
import tempfile
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


def _get_pltz_class():
    """Lazy import Pltz class."""
    from scitex.plt import Pltz

    return Pltz


class PltzPreviewService:
    """Service for pltz preview and rendering operations."""

    @staticmethod
    def get_preview_image(
        bundle_path: Union[str, Path], image_type: str = "png"
    ) -> Optional[bytes]:
        """Get preview image. Handles pltz inside figz bundles."""
        path_str = str(bundle_path)
        # Handle pltz embedded in figz (path like "Figure1.figz/A.pltz")
        if ".figz/" in path_str:
            from scitex.fig import Figz

            figz_path, panel_pltz = path_str.split(".figz/", 1)
            figz = Figz(figz_path + ".figz")
            pltz_bytes = figz.get_panel_pltz(panel_pltz.replace(".pltz", ""))
            if not pltz_bytes:
                return None
            with tempfile.NamedTemporaryFile(suffix=".pltz", delete=False) as f:
                f.write(pltz_bytes)
                temp_path = Path(f.name)
            try:
                pltz = _get_pltz_class()(temp_path)
                return pltz.get_preview() or pltz.render_preview()
            finally:
                temp_path.unlink(missing_ok=True)
        # Standard standalone pltz
        try:
            pltz = _get_pltz_class()(bundle_path)
            return pltz.get_preview() or pltz.render_preview()
        except Exception as e:
            logger.warning(f"Failed to get preview: {e}")
            return None

    @staticmethod
    def render_preview(bundle_path: Union[str, Path]) -> dict:
        """Re-render preview and update bundle."""
        pltz = _get_pltz_class()(bundle_path)
        pltz.update_preview()
        return {"path": str(bundle_path), "rendered": True}

    @staticmethod
    def get_preview_base64(
        bundle_path: Union[str, Path], image_type: str = "png"
    ) -> Optional[str]:
        """Get preview image as base64 data URL."""
        import base64

        data = PltzPreviewService.get_preview_image(bundle_path, image_type)
        if data:
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:image/png;base64,{b64}"
        return None
