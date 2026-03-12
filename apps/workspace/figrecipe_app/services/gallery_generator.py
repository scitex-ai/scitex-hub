"""
Gallery Generator Service

Generates example plots using scitex.plt.gallery into project workspace.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Ensure scitex is importable
SCITEX_CODE_PATH = os.environ.get(
    "SCITEX_CODE_PATH", "/home/ywatanabe/proj/scitex-code"
)
if SCITEX_CODE_PATH not in sys.path:
    sys.path.insert(0, f"{SCITEX_CODE_PATH}/src")


def get_gallery_path(project_path: Path) -> Path:
    """Get the gallery directory path within a project."""
    return project_path / "scitex" / "vis" / "gallery"


def get_template_gallery_path() -> Path:
    """Get the static gallery path (centralized server-side templates)."""
    from django.conf import settings

    return Path(settings.BASE_DIR) / "static" / "shared" / "images" / "gallery"


def generate_gallery(
    project_path: Path,
    category: Optional[str] = None,
    plot_type: Optional[str] = None,
    figsize: tuple = (4, 3),
    dpi: int = 150,
    force: bool = False,
) -> Dict:
    """
    Generate gallery plots into project's scitex/vis/gallery directory.

    Args:
        project_path: Path to project root
        category: Optional category to generate (line, statistical, etc.)
        plot_type: Optional specific plot type to generate
        figsize: Figure size (width, height) in inches
        dpi: Resolution for PNG output
        force: If True, regenerate even if gallery exists

    Returns:
        Dict with generation results
    """
    # Set matplotlib backend before importing scitex
    os.environ["MPLBACKEND"] = "Agg"

    try:
        import scitex as stx
    except ImportError as e:
        logger.error(f"Failed to import scitex: {e}")
        return {
            "success": False,
            "error": f"scitex not available: {e}",
            "png": [],
            "csv": [],
            "json": [],
        }

    gallery_path = get_gallery_path(project_path)

    # Check if gallery already exists
    if gallery_path.exists() and not force:
        existing_pngs = list(gallery_path.rglob("*.png"))
        if existing_pngs:
            logger.info(
                f"Gallery already exists at {gallery_path} with {len(existing_pngs)} plots"
            )
            return {
                "success": True,
                "message": "Gallery already exists",
                "path": str(gallery_path),
                "png": [str(p) for p in existing_pngs],
                "csv": [str(p) for p in gallery_path.rglob("*.csv")],
                "json": [str(p) for p in gallery_path.rglob("*.json")],
                "skipped": True,
            }

    # Ensure parent directories exist
    gallery_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Generating gallery at {gallery_path}")

    try:
        result = stx.plt.gallery.generate(
            output_dir=str(gallery_path),
            category=category,
            plot_type=plot_type,
            figsize=figsize,
            dpi=dpi,
            save_csv=True,
            save_png=True,
            verbose=True,
        )

        # Add JSON files to result
        json_files = list(gallery_path.rglob("*.json"))

        return {
            "success": True,
            "path": str(gallery_path),
            "png": result.get("png", []),
            "csv": result.get("csv", []),
            "json": [str(p) for p in json_files],
            "errors": result.get("errors", []),
        }

    except Exception as e:
        logger.exception(f"Failed to generate gallery: {e}")
        return {
            "success": False,
            "error": str(e),
            "png": [],
            "csv": [],
            "json": [],
        }


def list_gallery_categories() -> Dict:
    """List available gallery categories and plots."""
    os.environ["MPLBACKEND"] = "Agg"

    try:
        import scitex as stx

        categories = stx.plt.gallery.list_plots()
        return {
            "success": True,
            "categories": categories,
            "total_plots": sum(len(info["plots"]) for info in categories.values()),
        }
    except ImportError as e:
        logger.error(f"Failed to import scitex: {e}")
        return {
            "success": False,
            "error": str(e),
            "categories": {},
        }


def get_gallery_contents(project_path: Path, fallback_to_template: bool = True) -> Dict:
    """
    Get contents of an existing gallery.

    Args:
        project_path: Path to project root
        fallback_to_template: If True, use template gallery when project has none

    Returns:
        Dict with gallery contents organized by category
    """
    gallery_path = get_gallery_path(project_path)
    using_template = False

    if not gallery_path.exists():
        if fallback_to_template:
            # Try template gallery
            gallery_path = get_template_gallery_path()
            using_template = True
            if not gallery_path.exists():
                return {
                    "success": False,
                    "error": "Gallery not found",
                    "exists": False,
                    "categories": {},
                }
        else:
            return {
                "success": False,
                "error": "Gallery not found",
                "exists": False,
                "categories": {},
            }

    categories = {}

    # Scan gallery directory
    for category_dir in sorted(gallery_path.iterdir()):
        if not category_dir.is_dir():
            continue

        category_name = category_dir.name
        plots = []

        for png_file in sorted(category_dir.glob("*.png")):
            plot_name = png_file.stem
            json_file = category_dir / f"{plot_name}.json"
            csv_file = category_dir / f"{plot_name}.csv"

            plots.append(
                {
                    "name": plot_name,
                    "display_name": plot_name.replace("_", " ")
                    .replace("stx ", "")
                    .title(),
                    "png": str(png_file),
                    "json": str(json_file) if json_file.exists() else None,
                    "csv": str(csv_file) if csv_file.exists() else None,
                }
            )

        if plots:
            categories[category_name] = {
                "name": category_name.replace("_", " ").title(),
                "plots": plots,
                "count": len(plots),
            }

    total_plots = sum(cat["count"] for cat in categories.values())

    return {
        "success": True,
        "exists": True,
        "using_template": using_template,
        "path": str(gallery_path),
        "categories": categories,
        "total_plots": total_plots,
    }
