"""Gallery Pltz - Pltz bundle integration for the gallery."""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union

from .gallery_core import SCITEX_CODE_PATH, GalleryCore
from .pltz_service import PltzService

logger = logging.getLogger(__name__)


class GalleryPltz:
    """Service for pltz bundle integration with gallery."""

    @staticmethod
    def get_pltz_galleries() -> List[Dict]:
        """Get plot galleries that include pltz bundles."""
        galleries = GalleryCore.get_plot_galleries()

        pltz_gallery_paths = [
            SCITEX_CODE_PATH / "examples" / "scitex" / "fig",
            SCITEX_CODE_PATH / "examples" / "scitex" / "plt",
        ]

        for gallery_path in pltz_gallery_paths:
            if not gallery_path.exists():
                continue

            pltz_plots = GalleryPltz._scan_pltz_gallery(gallery_path)
            if pltz_plots:
                galleries.append(
                    {
                        "id": f"pltz_{gallery_path.name}",
                        "name": f"SciTeX {gallery_path.name.title()}",
                        "description": f"Pltz bundles from {gallery_path.name}",
                        "path": gallery_path,
                        "plots": pltz_plots,
                        "format": "pltz",
                    }
                )

        return galleries

    @staticmethod
    def _scan_pltz_gallery(base_path: Path) -> List[Dict]:
        """Scan directory for pltz bundles."""
        bundles = []

        for pltz_dir in sorted(base_path.glob("**/*.pltz.d")):
            if not PltzService.is_pltz_bundle(pltz_dir):
                continue

            try:
                bundle_data = PltzService.load_bundle(pltz_dir)
                spec = bundle_data.get("spec", {})
                style = bundle_data.get("style", {})

                plot_id = spec.get("plot_id", pltz_dir.stem.replace(".pltz", ""))
                display_name = plot_id.replace("_", " ").title()
                category = PltzService.categorize_plot(spec)

                bundle_info = {
                    "id": f"pltz_{plot_id}",
                    "name": display_name,
                    "category": category,
                    "format": "pltz",
                    "bundle_path": str(pltz_dir),
                    "spec": spec,
                    "style": style,
                    "files": {
                        "pltz": str(pltz_dir),
                        "png": bundle_data.get("exports", {}).get("png"),
                        "csv": (
                            str(pltz_dir / "data.csv")
                            if (pltz_dir / "data.csv").exists()
                            else None
                        ),
                    },
                }
                bundles.append(bundle_info)
            except Exception as e:
                logger.warning(f"Failed to load pltz bundle {pltz_dir}: {e}")

        return bundles

    @staticmethod
    def load_pltz_from_gallery(category: str, plot_name: str) -> Optional[Dict]:
        """Load a pltz bundle from the gallery."""
        from .gallery_generator import get_template_gallery_path

        gallery_path = get_template_gallery_path()
        pltz_path = gallery_path / category / f"{plot_name}.pltz.d"

        if pltz_path.exists() and PltzService.is_pltz_bundle(pltz_path):
            return PltzService.load_bundle(pltz_path)

        temp_gallery = Path("/tmp/scitex_gallery_with_bboxes")
        pltz_path = temp_gallery / category / f"{plot_name}.pltz.d"

        if pltz_path.exists() and PltzService.is_pltz_bundle(pltz_path):
            return PltzService.load_bundle(pltz_path)

        return None

    @staticmethod
    def get_pltz_preview_base64(category: str, plot_name: str) -> Optional[str]:
        """Get pltz bundle preview as base64 data URL."""
        from .gallery_generator import get_template_gallery_path

        gallery_path = get_template_gallery_path()
        pltz_path = gallery_path / category / f"{plot_name}.pltz.d"

        if pltz_path.exists():
            return PltzService.get_preview_base64(pltz_path)

        temp_gallery = Path("/tmp/scitex_gallery_with_bboxes")
        pltz_path = temp_gallery / category / f"{plot_name}.pltz.d"

        if pltz_path.exists():
            return PltzService.get_preview_base64(pltz_path)

        return None

    @staticmethod
    def convert_legacy_to_pltz(
        png_path: Union[str, Path],
        json_path: Optional[Union[str, Path]] = None,
        csv_path: Optional[Union[str, Path]] = None,
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Optional[Dict]:
        """Convert legacy gallery format (png/json/csv) to pltz bundle."""
        png_path = Path(png_path)
        plot_name = png_path.stem

        if output_dir:
            pltz_path = Path(output_dir) / f"{plot_name}.pltz.d"
        else:
            pltz_path = png_path.parent / f"{plot_name}.pltz.d"

        spec, style = {}, {}

        if json_path:
            json_path = Path(json_path)
            if json_path.exists():
                with open(json_path, "r") as f:
                    metadata = json.load(f)

                spec = {
                    "plot_id": plot_name,
                    "data": {"csv": "data.csv", "format": "wide"},
                    "axes": [],
                    "traces": [],
                }

                if "axes_bbox_px" in metadata:
                    spec["axes"].append({"id": "ax0", "role": "main", "labels": {}})

                if "dimensions" in metadata:
                    dims = metadata["dimensions"]
                    style["size"] = {
                        "width_mm": dims.get("width_mm", 80),
                        "height_mm": dims.get("height_mm", 60),
                    }

        csv_data = None
        if csv_path:
            csv_path = Path(csv_path)
            if csv_path.exists():
                with open(csv_path, "r") as f:
                    csv_data = f.read()

        try:
            result = PltzService.save_bundle(
                spec=spec or {"plot_id": plot_name},
                style=style or {},
                data_csv=csv_data,
                output_path=pltz_path,
                generate_exports=False,
            )

            exports_dir = pltz_path / "exports"
            exports_dir.mkdir(exist_ok=True)
            shutil.copy(png_path, exports_dir / f"{plot_name}.png")

            return result
        except Exception as e:
            logger.exception(f"Failed to convert to pltz: {e}")
            return None
