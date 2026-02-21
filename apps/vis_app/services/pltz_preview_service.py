"""PltzBundle Preview Service - Preview and rendering operations."""

import logging
import tempfile
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


class PltzPreviewService:
    """Service for pltz preview and rendering operations."""

    @staticmethod
    def get_preview_image(
        bundle_path: Union[str, Path], image_type: str = "png"
    ) -> Optional[bytes]:
        """Get preview image. Handles pltz inside figz bundles."""
        import figrecipe

        path_str = str(bundle_path)

        # Handle pltz embedded in figz (path like "Figure1.figz/A.pltz")
        if ".figz/" in path_str:
            figz_path_str, panel_part = path_str.split(".figz/", 1)
            figz = figrecipe.Figz(Path(figz_path_str + ".figz"))
            panel_id = panel_part.replace(".pltz", "").replace(".plt.zip", "")
            pltz_bytes = figz.get_panel_pltz(panel_id)
            if not pltz_bytes:
                return None
            tmp = Path(tempfile.mktemp(suffix=".plt.zip"))
            try:
                tmp.write_bytes(pltz_bytes)
                pltz = figrecipe.Pltz(tmp)
                return pltz.get_preview() or pltz.render_preview()
            finally:
                tmp.unlink(missing_ok=True)

        # Standard standalone pltz
        try:
            pltz = figrecipe.Pltz(bundle_path)
            return pltz.get_preview() or pltz.render_preview()
        except Exception as e:
            logger.warning(f"Failed to get preview: {e}")
            return None

    @staticmethod
    def render_preview(bundle_path: Union[str, Path]) -> dict:
        """Re-render preview and update bundle."""
        import figrecipe

        pltz = figrecipe.Pltz(bundle_path)
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
