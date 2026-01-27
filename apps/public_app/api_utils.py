#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API utility functions for public_app tools.
Helper functions for file handling and metadata extraction.
"""

import json
import logging
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("scitex")


def detect_bundle_type(filename: str) -> Optional[str]:
    """Detect if file is a SciTeX bundle (.pltz, .figz, .statsz)."""
    name_lower = filename.lower()
    for ext in [".pltz", ".figz", ".statsz"]:
        if name_lower.endswith(ext) or name_lower.endswith(f"{ext}.d"):
            return ext[1:]  # Return without dot
    return None


def read_bundle_metadata(bundle_path: Path, bundle_type: str) -> Dict[str, Any]:
    """Read metadata from a SciTeX bundle."""
    result = {
        "bundle_type": bundle_type,
        "spec": None,
        "has_png": False,
        "has_svg": False,
        "has_pdf": False,
        "has_csv": False,
        "panels": [],
        "plots": [],
    }

    spec_names = {
        "pltz": "plot.json",
        "figz": "figure.json",
        "statsz": "stats.json",
    }

    is_zip = zipfile.is_zipfile(str(bundle_path))

    if is_zip:
        _read_bundle_from_zip(bundle_path, bundle_type, spec_names, result)
    elif bundle_path.is_dir():
        _read_bundle_from_dir(bundle_path, bundle_type, spec_names, result)

    return result


def _read_bundle_from_zip(
    bundle_path: Path, bundle_type: str, spec_names: dict, result: dict
):
    """Read bundle metadata from ZIP file."""
    with zipfile.ZipFile(bundle_path, "r") as zf:
        file_list = zf.namelist()
        spec_name = spec_names.get(bundle_type)

        if spec_name and spec_name in file_list:
            with zf.open(spec_name) as f:
                result["spec"] = json.load(f)

        result["has_png"] = any(f.endswith(".png") for f in file_list)
        result["has_svg"] = any(f.endswith(".svg") for f in file_list)
        result["has_pdf"] = any(f.endswith(".pdf") for f in file_list)
        result["has_csv"] = any(f.endswith(".csv") for f in file_list)

        if bundle_type == "figz":
            result["panels"] = [f for f in file_list if ".pltz" in f]


def _read_bundle_from_dir(
    bundle_path: Path, bundle_type: str, spec_names: dict, result: dict
):
    """Read bundle metadata from directory."""
    spec_name = spec_names.get(bundle_type)

    if spec_name:
        spec_path = bundle_path / spec_name
        if spec_path.exists():
            with open(spec_path, "r") as f:
                result["spec"] = json.load(f)

    result["has_png"] = (bundle_path / "plot.png").exists() or any(
        bundle_path.glob("*.png")
    )
    result["has_svg"] = (bundle_path / "plot.svg").exists() or any(
        bundle_path.glob("*.svg")
    )
    result["has_pdf"] = (bundle_path / "plot.pdf").exists() or any(
        bundle_path.glob("*.pdf")
    )
    result["has_csv"] = (bundle_path / "plot.csv").exists() or any(
        bundle_path.glob("*.csv")
    )

    if bundle_type == "figz":
        result["panels"] = [d.name for d in bundle_path.iterdir() if ".pltz" in d.name]


def get_svg_dimensions(svg_path: str) -> Dict[str, Any]:
    """Extract dimensions from SVG file."""
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            content = f.read(2000)

        viewbox_match = re.search(r'viewBox=["\']([^"\']+)["\']', content)
        if viewbox_match:
            parts = viewbox_match.group(1).split()
            if len(parts) >= 4:
                return {
                    "width": float(parts[2]),
                    "height": float(parts[3]),
                    "unit": "viewBox",
                }

        width_match = re.search(r'width=["\']([0-9.]+)(px|pt|mm|in)?["\']', content)
        height_match = re.search(r'height=["\']([0-9.]+)(px|pt|mm|in)?["\']', content)

        if width_match and height_match:
            return {
                "width": float(width_match.group(1)),
                "height": float(height_match.group(1)),
                "unit": width_match.group(2) or "px",
            }

    except Exception as e:
        logger.warning(f"Failed to parse SVG dimensions: {e}")

    return {"width": None, "height": None, "unit": None}


def get_bundle_dimensions_from_png(bundle_path: Path) -> Optional[Dict[str, int]]:
    """Try to get dimensions from PNG in bundle."""
    try:
        if zipfile.is_zipfile(str(bundle_path)):
            with zipfile.ZipFile(bundle_path, "r") as zf:
                png_files = [f for f in zf.namelist() if f.endswith(".png")]
                if png_files:
                    import io

                    from PIL import Image

                    with zf.open(png_files[0]) as png_f:
                        img = Image.open(io.BytesIO(png_f.read()))
                        dims = {"width": img.width, "height": img.height}
                        img.close()
                        return dims
        elif bundle_path.is_dir():
            png_files = list(bundle_path.glob("*.png"))
            if png_files:
                from PIL import Image

                img = Image.open(png_files[0])
                dims = {"width": img.width, "height": img.height}
                img.close()
                return dims
    except Exception as e:
        logger.warning(f"Could not read bundle PNG dimensions: {e}")
    return None
