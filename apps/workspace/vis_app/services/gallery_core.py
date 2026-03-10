"""Gallery Core - Basic gallery scanning and plot operations."""

import base64
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Base path to scitex-code examples
SCITEX_CODE_PATH = Path(
    os.environ.get("SCITEX_CLOUD_CODE_PATH")
    or os.environ.get("SCITEX_CODE_PATH", "/home/ywatanabe/proj/scitex-code")
)
EXAMPLES_PATH = SCITEX_CODE_PATH / "examples" / "plt"


class GalleryCore:
    """Core gallery scanning and basic operations."""

    @staticmethod
    def get_plot_galleries() -> List[Dict]:
        """Get all plot galleries from examples directory."""
        galleries = []

        # Matplotlib basic plots
        mpl_out = EXAMPLES_PATH / "demo_matplotlib_basic_out"
        if mpl_out.exists():
            galleries.append(
                {
                    "id": "matplotlib",
                    "name": "Matplotlib",
                    "description": "Standard matplotlib plot types",
                    "path": mpl_out,
                    "plots": GalleryCore._scan_gallery(mpl_out, "mpl"),
                }
            )

        # SciTeX wrapper plots
        stx_out = EXAMPLES_PATH / "demo_scitex_wrappers_out"
        if stx_out.exists():
            galleries.append(
                {
                    "id": "scitex",
                    "name": "SciTeX",
                    "description": "SciTeX enhanced plot wrappers",
                    "path": stx_out,
                    "plots": GalleryCore._scan_gallery(stx_out, "stx"),
                }
            )

        # Seaborn wrapper plots
        sns_out = EXAMPLES_PATH / "demo_seaborn_wrappers_out"
        if sns_out.exists():
            galleries.append(
                {
                    "id": "seaborn",
                    "name": "Seaborn",
                    "description": "Seaborn statistical plots",
                    "path": sns_out,
                    "plots": GalleryCore._scan_gallery(sns_out, "sns"),
                }
            )

        return galleries

    @staticmethod
    def _scan_gallery(base_path: Path, prefix: str) -> List[Dict]:
        """Scan gallery directory for plot types."""
        plots = []
        png_dir = base_path / "png"
        json_dir = base_path / "json"
        csv_dir = base_path / "csv"

        if not png_dir.exists():
            return plots

        for png_file in sorted(png_dir.glob("*.png")):
            stem = png_file.stem
            json_file = json_dir / f"{stem}.json"
            csv_file = csv_dir / f"{stem}.csv"

            parts = stem.split("_", 1)
            number = parts[0] if len(parts) > 1 else ""
            name_part = parts[1] if len(parts) > 1 else stem
            display_name = name_part.replace("_", " ").title()
            category = GalleryCore._categorize_plot(name_part)

            plot_info = {
                "id": f"{prefix}_{stem}",
                "name": display_name,
                "category": category,
                "number": number,
                "files": {
                    "png": str(png_file),
                    "json": str(json_file) if json_file.exists() else None,
                    "csv": str(csv_file) if csv_file.exists() else None,
                },
            }
            plots.append(plot_info)

        return plots

    @staticmethod
    def _categorize_plot(name: str) -> str:
        """Categorize plot by type based on name."""
        name_lower = name.lower()

        categories = {
            "line": ["line", "plot", "step", "mean", "median", "shaded"],
            "scatter": ["scatter"],
            "bar": ["bar", "barh"],
            "distribution": ["hist", "kde", "ecdf"],
            "statistical": ["box", "violin", "strip", "swarm", "joyplot"],
            "heatmap": ["heatmap", "imshow", "matshow", "conf_mat", "image"],
            "contour": ["contour", "hexbin", "fill"],
            "pie": ["pie"],
            "vector": ["quiver", "stream", "raster"],
            "error": ["errorbar"],
            "stem": ["stem"],
        }

        for cat, keywords in categories.items():
            if any(x in name_lower for x in keywords):
                return cat
        return "other"

    @staticmethod
    def find_plot_in_galleries(
        gallery_id: str, plot_id: str
    ) -> Optional[Tuple[Dict, Dict]]:
        """Find a plot in galleries."""
        galleries = GalleryCore.get_plot_galleries()
        gallery = next((g for g in galleries if g["id"] == gallery_id), None)

        if not gallery:
            return None

        plot = next(
            (p for p in gallery["plots"] if p["id"] == f"{gallery_id[:3]}_{plot_id}"),
            None,
        )

        if not plot:
            plot = next((p for p in gallery["plots"] if plot_id in p["id"]), None)

        if not plot:
            return None

        return gallery, plot

    @staticmethod
    def load_thumbnail(png_path: Path) -> bytes:
        """Load thumbnail image data."""
        if not png_path.exists():
            raise FileNotFoundError(f"Thumbnail file not found: {png_path}")
        with open(png_path, "rb") as f:
            return f.read()

    @staticmethod
    def encode_thumbnail_base64(image_data: bytes) -> str:
        """Encode image data as base64 data URL."""
        b64_data = base64.b64encode(image_data).decode("utf-8")
        return f"data:image/png;base64,{b64_data}"
