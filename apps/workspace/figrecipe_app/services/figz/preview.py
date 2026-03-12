#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preview generation for FigzBundle."""

from __future__ import annotations

import base64
import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional, Union

logger = logging.getLogger(__name__)


def get_preview_image(
    bundle_path: Union[str, Path], image_type: str = "png"
) -> Optional[bytes]:
    """Get composed figure preview image."""
    import figrecipe

    try:
        figz = figrecipe.Figz(bundle_path)
        return figz.render_preview()
    except Exception as e:
        logger.warning(f"Failed to get preview: {e}")
        return None


def get_preview_base64(
    bundle_path: Union[str, Path], image_type: str = "png"
) -> Optional[str]:
    """Get preview image as base64 data URL."""
    data = get_preview_image(bundle_path, image_type)
    if data:
        return f"data:image/png;base64,{base64.b64encode(data).decode('utf-8')}"
    return None


def get_panel_previews(bundle_path: Union[str, Path]) -> Dict[str, Optional[str]]:
    """Get preview images for all panels as base64."""
    import figrecipe

    result = {}
    try:
        figz = figrecipe.Figz(bundle_path)
        for panel_id in figz.list_panel_ids():
            pltz_bytes = figz.get_panel_pltz(panel_id)
            if pltz_bytes:
                tmp = Path(tempfile.mktemp(suffix=".plt.zip"))
                try:
                    tmp.write_bytes(pltz_bytes)
                    pltz = figrecipe.Pltz(tmp)
                    preview = pltz.get_preview() or pltz.render_preview()
                    if preview:
                        result[panel_id] = (
                            f"data:image/png;base64,"
                            f"{base64.b64encode(preview).decode('utf-8')}"
                        )
                finally:
                    if tmp.exists():
                        tmp.unlink()
    except Exception as e:
        logger.warning(f"Failed to get panel previews: {e}")
    return result


# EOF
