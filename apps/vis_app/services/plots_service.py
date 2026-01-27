"""
Plots Service - Business logic for plot rendering operations.

Re-exports from specialized submodules:
- plots_data: Data detection and preparation
- plots_render: Plot rendering by type
- plots_metadata: Image metadata extraction
- plots_files: File upload handling
"""

import base64
import io
import logging
import os
from typing import Dict, List, Tuple

import numpy as np

from .plots_data import detect_xy_column_pairs, prepare_dataframe
from .plots_files import save_uploaded_file
from .plots_metadata import extract_image_metadata_from_base64, extract_metadata_fields
from .plots_render import apply_plot_styling, render_plot_by_type

logger = logging.getLogger(__name__)


class PlotsService:
    """Service for plot rendering operations (delegates to specialized modules)."""

    # Data operations
    detect_xy_column_pairs = staticmethod(detect_xy_column_pairs)
    prepare_dataframe = staticmethod(prepare_dataframe)

    # Render operations
    @staticmethod
    def render_plot_by_type(ax, df, plot_type: str, category: str, overrides: dict):
        """Render plot based on type."""
        cols = df.columns.tolist()
        xy_pairs = detect_xy_column_pairs(cols)
        render_plot_by_type(ax, df, plot_type, category, overrides, xy_pairs)

    apply_plot_styling = staticmethod(apply_plot_styling)

    # File operations
    save_uploaded_file = staticmethod(save_uploaded_file)

    # Metadata operations
    extract_image_metadata_from_base64 = staticmethod(
        extract_image_metadata_from_base64
    )
    _extract_metadata_fields = staticmethod(extract_metadata_fields)

    @staticmethod
    def render_gallery_plot(
        plot_type: str, category: str, csv_data: List[List], overrides: dict
    ) -> Dict:
        """Render a plot from gallery template with CSV data."""
        os.environ["MPLBACKEND"] = "Agg"

        try:
            import scitex as stx
        except ImportError as e:
            raise ImportError(f"scitex not available: {e}")

        df = prepare_dataframe(csv_data)
        fig_width = overrides.get("fig_width", 4)
        fig_height = overrides.get("fig_height", 3)
        dpi = overrides.get("dpi", 150)

        fig, ax = stx.plt.subplots(figsize=(fig_width, fig_height))
        cols = df.columns.tolist()
        xy_pairs = detect_xy_column_pairs(cols)

        render_plot_by_type(ax, df, plot_type, category, overrides, xy_pairs)
        apply_plot_styling(ax, overrides)
        fig.tight_layout()

        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=dpi,
            bbox_inches="tight",
            transparent=True,
            facecolor="none",
            edgecolor="none",
        )
        buf.seek(0)

        from PIL import Image

        img = Image.open(buf)
        width, height = img.size
        buf.seek(0)

        from apps.vis_app.services.plot_renderer.element_bboxes import (
            extract_element_bboxes,
        )

        element_bboxes = extract_element_bboxes(fig, ax, renderer, width, height)

        hitmap_data, hitmap_color_map = _generate_hitmap(fig, dpi)

        if xy_pairs:
            y_cols = [pair[1] for pair in xy_pairs]
        else:
            y_cols = overrides.get("y_columns", cols[1:] if len(cols) > 1 else [])
        if isinstance(y_cols, str):
            y_cols = [y_cols]

        column_mapping = _map_elements_to_columns(element_bboxes, y_cols, xy_pairs)
        b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")

        result = {
            "success": True,
            "image": f"data:image/png;base64,{b64_data}",
            "width": width,
            "height": height,
            "element_bboxes": element_bboxes,
            "column_mapping": column_mapping,
        }

        if hitmap_data and hitmap_color_map:
            result["hitmap"] = hitmap_data
            result["hitmap_color_map"] = hitmap_color_map

        return result


def _generate_hitmap(fig, dpi):
    """Generate hitmap for element picking."""
    try:
        from scitex.plt.utils._hitmap import generate_hitmap_id_colors

        hitmap, color_map = generate_hitmap_id_colors(fig, dpi=dpi)
        hitmap_buf = io.BytesIO()
        from PIL import Image as PILImage

        h, w = hitmap.shape
        rgb = np.zeros((h, w, 3), dtype=np.uint8)
        rgb[:, :, 0] = (hitmap >> 16) & 0xFF
        rgb[:, :, 1] = (hitmap >> 8) & 0xFF
        rgb[:, :, 2] = hitmap & 0xFF
        hitmap_img = PILImage.fromarray(rgb, mode="RGB")
        hitmap_img.save(hitmap_buf, format="PNG")
        hitmap_buf.seek(0)
        hitmap_data = f"data:image/png;base64,{base64.b64encode(hitmap_buf.getvalue()).decode('utf-8')}"
        hitmap_color_map = {str(k): v for k, v in color_map.items()}
        logger.info(f"[PlotsService] Generated hitmap with {len(color_map)} elements")
        return hitmap_data, hitmap_color_map
    except Exception as e:
        logger.debug(f"[PlotsService] Hitmap generation skipped: {e}")
        return None, None


def _map_elements_to_columns(
    element_bboxes: Dict, y_cols: List[str], xy_pairs: List[Tuple[str, str, str]]
) -> Dict[str, str]:
    """Map element names to their CSV columns."""
    column_mapping = {}

    for element_name, bbox in element_bboxes.items():
        element_type = bbox.get("element_type", "")
        label = bbox.get("label", "")

        if element_type in ["line", "scatter"]:
            trace_idx = bbox.get("trace_idx")
            matched_y_col = None

            if trace_idx is not None and trace_idx < len(y_cols):
                matched_y_col = y_cols[trace_idx]
            elif label:
                for idx, y_col in enumerate(y_cols):
                    if label == y_col or (
                        xy_pairs and idx < len(xy_pairs) and label == xy_pairs[idx][2]
                    ):
                        matched_y_col = y_col
                        break

            if matched_y_col:
                column_mapping[element_name] = matched_y_col

    return column_mapping


__all__ = [
    "PlotsService",
    "detect_xy_column_pairs",
    "prepare_dataframe",
    "render_plot_by_type",
    "apply_plot_styling",
    "save_uploaded_file",
    "extract_image_metadata_from_base64",
]
