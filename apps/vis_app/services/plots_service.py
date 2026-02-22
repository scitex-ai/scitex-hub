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
        """Render a plot from gallery template with CSV data using figrecipe."""
        import json as _json
        import tempfile
        import zipfile as _zipfile
        from pathlib import Path as _Path

        os.environ["MPLBACKEND"] = "Agg"

        try:
            import figrecipe as fr
        except ImportError as e:
            raise ImportError(f"figrecipe not available: {e}")

        # Re-apply scitex rcParams (Celery workers may reset matplotlib state)
        try:
            from scitex.plt._auto_config import _apply_rcparams

            try:
                from figrecipe import load_style as _fr_load_style

                _apply_rcparams(True, _fr_load_style)
            except ImportError:
                _apply_rcparams(False, lambda _: None)
        except Exception as _rc_err:
            logger.warning(
                f"[PlotsService] rcParams apply failed: {_rc_err}", exc_info=True
            )

        df = prepare_dataframe(csv_data)
        fig_width = overrides.get("fig_width", 4)
        fig_height = overrides.get("fig_height", 3)
        dpi = overrides.get("dpi", 150)

        cols = df.columns.tolist()
        xy_pairs = detect_xy_column_pairs(cols)

        # Use figrecipe.subplots() with mm-based margins — no tight_layout needed
        fig, ax = fr.subplots(
            figsize=(fig_width, fig_height),
            margin_left_mm=12,
            margin_bottom_mm=12,
            margin_right_mm=5,
            margin_top_mm=5,
        )

        render_plot_by_type(ax, df, plot_type, category, overrides, xy_pairs)
        apply_plot_styling(ax, overrides)

        # Auto-set axis labels from column names if not already set via overrides
        if not ax.get_xlabel() and not overrides.get("xlabel"):
            x_col = xy_pairs[0][0] if xy_pairs else (cols[0] if cols else None)
            if x_col and "_variable-" not in x_col:
                ax.set_xlabel(x_col)
        if not ax.get_ylabel() and not overrides.get("ylabel"):
            y_col = xy_pairs[0][1] if xy_pairs else (cols[1] if len(cols) > 1 else None)
            if y_col and "_variable-" not in y_col:
                ax.set_ylabel(y_col)

        # Access underlying mpl figure for renderer (needed by element_bboxes/hitmap extractors)
        mpl_fig = fig.fig if hasattr(fig, "fig") else fig
        mpl_fig.canvas.draw()
        renderer = mpl_fig.canvas.get_renderer()

        # Save via figrecipe — produces .plt.zip with recipe.yaml (reproducible)
        pltz_bytes = None
        png_bytes = None
        element_bboxes = {}
        hitmap_data = None
        hitmap_color_map = None
        column_mapping = {}
        width = 0
        height = 0

        tmp_path = _Path(tempfile.mktemp(suffix=".plt.zip"))
        try:
            from figrecipe._bundle._save import save_bundle

            save_bundle(fig, tmp_path, dpi=dpi, verbose=False)

            # Extract PNG from bundle (figrecipe saves to exports/figure.png)
            with _zipfile.ZipFile(tmp_path) as zf:
                names = zf.namelist()
                prefix = (
                    names[0].split("/")[0] + "/" if names and "/" in names[0] else ""
                )
                png_name = next(
                    (n for n in names if n.endswith(".png") and "hitmap" not in n),
                    None,
                )
                if not png_name:
                    raise RuntimeError(
                        f"No PNG found in figrecipe bundle. Contents: {names}"
                    )
                png_bytes = zf.read(png_name)

            from PIL import Image

            img = Image.open(io.BytesIO(png_bytes))
            width, height = img.size

            from apps.vis_app.services.plot_renderer.element_bboxes import (
                extract_element_bboxes,
            )

            mpl_ax = mpl_fig.axes[0] if mpl_fig.axes else None
            if mpl_ax:
                element_bboxes = extract_element_bboxes(
                    mpl_fig, mpl_ax, renderer, width, height
                )

            hitmap_data, hitmap_color_map = _generate_hitmap(mpl_fig, dpi)

            if xy_pairs:
                y_cols = [pair[1] for pair in xy_pairs]
            else:
                y_cols = overrides.get("y_columns", cols[1:] if len(cols) > 1 else [])
            if isinstance(y_cols, str):
                y_cols = [y_cols]
            column_mapping = _map_elements_to_columns(element_bboxes, y_cols, xy_pairs)

            # Append element_bboxes and hitmap_color_map to the bundle
            hitmap_bytes = (
                base64.b64decode(hitmap_data.split(",", 1)[-1]) if hitmap_data else None
            )
            with _zipfile.ZipFile(tmp_path, "a") as zf:
                if element_bboxes:
                    zf.writestr(
                        f"{prefix}metadata/element_bboxes.json",
                        _json.dumps(element_bboxes),
                    )
                if hitmap_color_map:
                    zf.writestr(
                        f"{prefix}metadata/hitmap_color_map.json",
                        _json.dumps({str(k): v for k, v in hitmap_color_map.items()}),
                    )
                if hitmap_bytes:
                    zf.writestr(f"{prefix}exports/hitmap.png", hitmap_bytes)

            pltz_bytes = tmp_path.read_bytes()

        except Exception as e:
            logger.error(
                f"[PlotsService] Failed to render via figrecipe bundle: {e}",
                exc_info=True,
            )
            raise
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        b64_data = base64.b64encode(png_bytes).decode("utf-8")

        result = {
            "success": True,
            "image": f"data:image/png;base64,{b64_data}",
            "width": width,
            "height": height,
            "element_bboxes": element_bboxes,
            "column_mapping": column_mapping,
        }

        if pltz_bytes:
            result["pltz_b64"] = base64.b64encode(pltz_bytes).decode("utf-8")

        if hitmap_data and hitmap_color_map:
            result["hitmap"] = hitmap_data
            result["hitmap_color_map"] = hitmap_color_map

        return result


def _generate_hitmap(fig, dpi):
    """Generate hitmap for element picking."""
    try:
        from scitex.plt.utils._hitmap import generate_hitmap_id_colors

        # Unwrap RecordingFigure to get underlying matplotlib Figure
        mpl_fig = fig.fig if hasattr(fig, "fig") else fig
        hitmap, color_map = generate_hitmap_id_colors(mpl_fig, dpi=dpi)
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
