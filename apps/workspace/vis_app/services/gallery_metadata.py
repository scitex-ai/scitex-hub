"""Gallery Metadata - Template loading, metadata extraction, and categorization."""

import base64
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class GalleryMetadata:
    """Service for loading plot metadata and templates."""

    @staticmethod
    def load_plot_template(plot: Dict) -> Dict:
        """Load plot template data (JSON metadata and CSV columns)."""
        result = {
            "id": plot["id"],
            "name": plot["name"],
            "category": plot["category"],
        }

        if plot["files"]["json"]:
            json_path = Path(plot["files"]["json"])
            if json_path.exists():
                with open(json_path, "r") as f:
                    result["metadata"] = json.load(f)
                if "axes_bbox_px" in result["metadata"]:
                    result["axes_bbox_px"] = result["metadata"]["axes_bbox_px"]

        if plot["files"]["csv"]:
            csv_path = Path(plot["files"]["csv"])
            if csv_path.exists():
                with open(csv_path, "r") as f:
                    header = f.readline().strip()
                    result["csv_columns"] = header.split(",")

        return result

    @staticmethod
    def generate_boilerplate(plot: dict, gallery_id: str) -> str:
        """Generate Python boilerplate code for the plot type."""
        name = plot["name"].lower().replace(" ", "_")
        templates = {
            "matplotlib": f'import scitex as stx\n\nfig, ax = stx.plt.subplots()\n# ax.{name}(x, y)\nstx.io.save(fig, "output/{name}.png")\n',
            "scitex": f'import scitex as stx\n\nfig, ax = stx.plt.subplots()\n# ax.stx_{name.replace("stx_", "").replace("plot_", "")}(x, y)\nstx.io.save(fig, "output/stx_{name.replace("stx_", "").replace("plot_", "")}.png")\n',
            "seaborn": f'import scitex as stx\n\nfig, ax = stx.plt.subplots()\n# ax.sns_{name.replace("sns_", "")}(data=df, x="x", y="y")\nstx.io.save(fig, "output/sns_{name.replace("sns_", "")}.png")\n',
        }
        return templates.get(gallery_id, "# Plot code here")

    @staticmethod
    def get_category_counts(galleries: List[Dict]) -> Dict[str, int]:
        """Count plots by category across galleries."""
        category_counts = {}
        for gallery in galleries:
            for plot in gallery["plots"]:
                cat = plot["category"]
                category_counts[cat] = category_counts.get(cat, 0) + 1
        return category_counts

    @staticmethod
    def format_categories(category_counts: Dict[str, int]) -> List[Dict]:
        """Format category counts into display-ready list."""
        category_names = {
            "line": "Line Plots",
            "scatter": "Scatter Plots",
            "bar": "Bar Charts",
            "distribution": "Distributions",
            "statistical": "Statistical",
            "heatmap": "Heatmaps",
            "contour": "Contours",
            "pie": "Pie Charts",
            "vector": "Vector Fields",
            "error": "Error Bars",
            "stem": "Stem Plots",
            "other": "Other",
        }

        return [
            {
                "id": cat_id,
                "name": category_names.get(cat_id, cat_id.title()),
                "count": count,
            }
            for cat_id, count in sorted(category_counts.items(), key=lambda x: -x[1])
        ]

    @staticmethod
    def load_plot_metadata(category: str, plot_name: str) -> Optional[Dict]:
        """Load plot metadata (axes_bbox_px, figure_size_px, element_bboxes)."""
        from .gallery_generator import get_template_gallery_path

        # Try temp gallery first
        temp_gallery_path = Path("/tmp/scitex_gallery_with_bboxes")
        json_path = temp_gallery_path / category / f"{plot_name}.json"

        if not json_path.exists():
            gallery_path = get_template_gallery_path()
            json_path = gallery_path / category / f"{plot_name}.json"

        if not json_path.exists():
            json_path = GalleryMetadata._find_in_static_gallery(category, plot_name)

        if not json_path or not json_path.exists():
            return None

        with open(json_path, "r") as f:
            metadata = json.load(f)

        result = GalleryMetadata._extract_metadata_fields(metadata)

        # Load hitmap PNG if available
        if result and result.get("hitmap_file"):
            hitmap_path = json_path.parent / result["hitmap_file"]
            if hitmap_path.exists():
                try:
                    with open(hitmap_path, "rb") as f:
                        hitmap_data = f.read()
                    hitmap_b64 = base64.b64encode(hitmap_data).decode("utf-8")
                    result["hitmap"] = f"data:image/png;base64,{hitmap_b64}"
                except Exception as e:
                    logger.warning(f"Failed to load hitmap: {e}")

        return result

    @staticmethod
    def _find_in_static_gallery(category: str, plot_name: str) -> Optional[Path]:
        """Find JSON file in static gallery directories."""
        base = Path(settings.BASE_DIR) / "apps/vis_app/static/vis_app/img/plot_gallery"
        for subdir in ["01_matplotlib_basic", "02_custom_scitex", "04_seaborn"]:
            alt_path = base / subdir
            if not alt_path.exists():
                continue
            for json_file in alt_path.glob("*.json"):
                stem = (
                    json_file.stem.split("_", 1)[-1]
                    if "_" in json_file.stem
                    else json_file.stem
                )
                if (
                    stem.lower() == plot_name.lower()
                    or plot_name.lower() in json_file.stem.lower()
                ):
                    return json_file
        return None

    @staticmethod
    def _extract_metadata_fields(metadata: Dict) -> Optional[Dict]:
        """Extract axes_bbox_px, figure_size_px, and element_bboxes from metadata."""
        axes_bbox_px = metadata.get("axes_bbox_px")
        dimensions = metadata.get("dimensions", {})
        figure_size_px = dimensions.get("figure_size_px")
        element_bboxes = metadata.get("element_bboxes")

        # Try new schema format
        if not axes_bbox_px and "axes" in metadata:
            for ax_id, ax_info in metadata.get("axes", {}).items():
                if "bbox_px" in ax_info:
                    axes_bbox_px = ax_info["bbox_px"]
                    break

        if not figure_size_px and "figure" in metadata:
            fig_data = metadata.get("figure", {})
            size_px = fig_data.get("size_px")
            if size_px and isinstance(size_px, list) and len(size_px) == 2:
                figure_size_px = size_px

        # Extract element bboxes from new schema
        axes_bboxes = {}
        if "axes" in metadata:
            for ax_id, ax_info in metadata["axes"].items():
                if "bbox_px" in ax_info:
                    axes_bboxes[ax_id] = ax_info["bbox_px"]

        if not element_bboxes and "elements" in metadata:
            element_bboxes = GalleryMetadata._transform_element_bboxes(
                metadata.get("elements", {}), axes_bboxes
            )

        if not axes_bbox_px:
            return None

        response_data = {
            "success": True,
            "axes_bbox_px": axes_bbox_px,
            "figure_size_px": (
                {
                    "width": (
                        figure_size_px[0]
                        if isinstance(figure_size_px, list)
                        else figure_size_px.get("width")
                    ),
                    "height": (
                        figure_size_px[1]
                        if isinstance(figure_size_px, list)
                        else figure_size_px.get("height")
                    ),
                }
                if figure_size_px
                else None
            ),
        }

        if element_bboxes:
            response_data["element_bboxes"] = element_bboxes

        hitmap_color_map = metadata.get("hitmap_color_map")
        hitmap_file = metadata.get("hitmap_file")
        if hitmap_color_map:
            response_data["hitmap_color_map"] = hitmap_color_map
        if hitmap_file:
            response_data["hitmap_file"] = hitmap_file

        return response_data

    @staticmethod
    def _transform_element_bboxes(elements_data: Dict, axes_bboxes: Dict) -> Dict:
        """Transform element bboxes from axes-local to figure-local coordinates."""
        element_bboxes = {}
        for elem_id, elem_info in elements_data.items():
            geometry = elem_info.get("geometry_px", {})
            bbox = geometry.get("bbox")
            if not bbox:
                continue

            coord_space = geometry.get("coord_space", "figure")
            axes_id = elem_info.get("axes_id")
            path_simplified = geometry.get("path_simplified")

            if coord_space == "axes" and axes_id and axes_id in axes_bboxes:
                ax_bbox = axes_bboxes[axes_id]
                ax_x0 = ax_bbox.get("x0", 0)
                ax_y0 = ax_bbox.get("y0", 0)

                bbox = {
                    "x0": bbox["x0"] + ax_x0,
                    "y0": bbox["y0"] + ax_y0,
                    "x1": bbox["x1"] + ax_x0,
                    "y1": bbox["y1"] + ax_y0,
                }

                if path_simplified:
                    path_simplified = [
                        [pt[0] + ax_x0, pt[1] + ax_y0] for pt in path_simplified
                    ]

            element_bboxes[elem_id] = {
                "bbox": bbox,
                "element_type": elem_info.get("element_type"),
                "label": elem_info.get("label"),
                "axes_id": axes_id,
                "path_simplified": path_simplified,
            }

        return element_bboxes
