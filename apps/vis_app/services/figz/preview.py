#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preview generation for FigzBundle."""

from __future__ import annotations

import base64
import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional, Union

from .constants import get_figz_class

logger = logging.getLogger(__name__)


def get_preview_image(
    bundle_path: Union[str, Path], image_type: str = "png"
) -> Optional[bytes]:
    """Get composed figure preview image."""
    Figz = get_figz_class()
    try:
        figz = Figz(bundle_path)
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
    Figz = get_figz_class()
    from scitex.plt import Pltz

    result = {}
    try:
        figz = Figz(bundle_path)
        for panel_id in figz.list_panel_ids():
            pltz_bytes = figz.get_panel_pltz(panel_id)
            if pltz_bytes:
                with tempfile.NamedTemporaryFile(suffix=".pltz", delete=False) as f:
                    f.write(pltz_bytes)
                    temp_path = f.name
                try:
                    pltz = Pltz(temp_path)
                    preview = pltz.get_preview() or pltz.render_preview()
                    result[panel_id] = (
                        f"data:image/png;base64,{base64.b64encode(preview).decode('utf-8')}"
                    )
                finally:
                    Path(temp_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Failed to get panel previews: {e}")
    return result


# EOF
