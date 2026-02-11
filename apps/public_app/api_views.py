#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API views for public_app tools.

Provides backend functionality for browser-based tools that require
server-side processing.

Re-exports from specialized submodules:
- api_utils: Helper functions for file handling
- api_docx: DOCX to LaTeX conversion
"""

import json
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .api_docx import docx2tex_convert
from .api_stats import (
    stats_calculate,
    stats_correct,
    stats_describe,
    stats_effect_size,
    stats_flowchart,  # noqa: F401
    stats_posthoc,
    stats_power,
    stats_recommend,
)
from .api_utils import (
    detect_bundle_type,
    get_bundle_dimensions_from_png,
    get_svg_dimensions,
    read_bundle_metadata,
)

# Django views use standard logging, not @stx.session injection
logger = logging.getLogger("scitex")  # noqa: STX-I007

# Re-export for backward compatibility
__all__ = [
    "read_image_metadata",
    "docx2tex_convert",
    "stats_calculate",
    "stats_correct",
    "stats_describe",
    "stats_effect_size",
    "stats_flowchart",
    "stats_posthoc",
    "stats_power",
    "stats_recommend",
]


@csrf_exempt
@require_http_methods(["POST"])
def read_image_metadata(request):
    """
    Read embedded metadata and file info from uploaded file.

    Supports:
    - Images: PNG, JPEG, SVG, WEBP, GIF, TIFF, BMP
    - Documents: PDF
    - SciTeX Bundles: .pltz, .pltz.d, .figz, .figz.d, .statsz, .statsz.d
    """
    try:
        if "image" not in request.FILES:
            return JsonResponse(
                {"error": "No file provided", "has_metadata": False}, status=400
            )

        uploaded_file = request.FILES["image"]
        filename = uploaded_file.name
        file_ext = filename.split(".")[-1].lower()
        bundle_type = detect_bundle_type(filename)

        suffix = _get_temp_suffix(filename, bundle_type, file_ext)
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)

        for chunk in uploaded_file.chunks():
            tmp_file.write(chunk)
        tmp_file.close()
        tmp_path = Path(tmp_file.name)

        try:
            from scitex.io import load, read_metadata

            if bundle_type:
                return _handle_bundle(tmp_path, bundle_type)
            elif file_ext == "svg":
                return _handle_svg(tmp_path)
            elif file_ext == "pdf":
                return _handle_pdf(tmp_path, read_metadata, load)
            else:
                return _handle_raster_image(tmp_path, file_ext, read_metadata, load)

        finally:
            _cleanup_temp(tmp_path)

    except ImportError as e:
        logger.error(f"Failed to import scitex.io: {e}")
        return JsonResponse(
            {
                "error": "Metadata extraction not available (scitex.io not installed)",
                "has_metadata": False,
            },
            status=500,
        )

    except Exception as e:
        logger.error(f"Error reading file metadata: {e}")
        return JsonResponse(
            {"error": f"Failed to read metadata: {str(e)}", "has_metadata": False},
            status=500,
        )


def _get_temp_suffix(filename: str, bundle_type, file_ext: str) -> str:
    """Get appropriate temp file suffix."""
    if bundle_type:
        for ext in [".pltz.d", ".figz.d", ".statsz.d", ".pltz", ".figz", ".statsz"]:
            if filename.lower().endswith(ext):
                return ext
    return f".{file_ext}"


def _handle_bundle(tmp_path: Path, bundle_type: str) -> JsonResponse:
    """Handle SciTeX bundle files."""
    bundle_info = read_bundle_metadata(tmp_path, bundle_type)

    response_data = {
        "has_metadata": bundle_info["spec"] is not None,
        "metadata": bundle_info["spec"],
        "file_type": f"bundle_{bundle_type}",
        "bundle_info": {
            "type": bundle_type,
            "has_png": bundle_info["has_png"],
            "has_svg": bundle_info["has_svg"],
            "has_pdf": bundle_info["has_pdf"],
            "has_csv": bundle_info["has_csv"],
            "panels": bundle_info.get("panels", []),
        },
        "message": f"SciTeX {bundle_type.upper()} bundle loaded",
    }

    if bundle_info["has_png"]:
        dims = get_bundle_dimensions_from_png(tmp_path)
        if dims:
            response_data["dimensions"] = dims

    return JsonResponse(response_data)


def _handle_svg(tmp_path: Path) -> JsonResponse:
    """Handle SVG files."""
    svg_dims = get_svg_dimensions(str(tmp_path))
    metadata = None

    try:
        with open(tmp_path, "r", encoding="utf-8") as f:
            content = f.read()
            meta_match = re.search(
                r"<!--\s*scitex_metadata:\s*(\{.*?\})\s*-->", content, re.DOTALL
            )
            if meta_match:
                metadata = json.loads(meta_match.group(1))
    except Exception as e:
        logger.warning(f"Failed to extract SVG metadata: {e}")

    return JsonResponse(
        {
            "has_metadata": metadata is not None,
            "metadata": metadata,
            "file_type": "svg",
            "dimensions": {
                "width": svg_dims.get("width"),
                "height": svg_dims.get("height"),
                "unit": svg_dims.get("unit", "px"),
            },
            "message": "SVG file loaded (vector format)",
        }
    )


def _handle_pdf(tmp_path: Path, read_metadata, load) -> JsonResponse:
    """Handle PDF files."""
    metadata = read_metadata(str(tmp_path))
    pdf_data = load(str(tmp_path), mode="metadata")

    response_data = {
        "has_metadata": metadata is not None,
        "metadata": metadata,
        "file_type": "pdf",
        "page_count": pdf_data.get("pages", 0),
        "dimensions": {
            "width_pt": None,
            "height_pt": None,
            "pages": pdf_data.get("pages", 0),
        },
        "pdf_metadata": {
            "title": pdf_data.get("title", ""),
            "author": pdf_data.get("author", ""),
            "subject": pdf_data.get("subject", ""),
            "creator": pdf_data.get("creator", ""),
        },
    }

    response_data["message"] = (
        "Metadata successfully extracted"
        if metadata
        else "No SciTeX metadata found in PDF"
    )
    return JsonResponse(response_data)


def _handle_raster_image(tmp_path: Path, file_ext: str, read_metadata, load):
    """Handle raster image files."""
    metadata = read_metadata(str(tmp_path))
    img, _ = load(str(tmp_path), metadata=True)

    response_data = {
        "has_metadata": metadata is not None,
        "metadata": metadata,
        "file_type": "image",
        "dimensions": {"width": img.width, "height": img.height},
    }

    img.close()

    response_data["message"] = (
        "Metadata successfully extracted"
        if metadata
        else f"No SciTeX metadata found in {file_ext.upper()}"
    )
    return JsonResponse(response_data)


def _cleanup_temp(tmp_path: Path):
    """Clean up temporary file or directory."""
    if tmp_path.exists():
        if tmp_path.is_dir():
            shutil.rmtree(tmp_path)
        else:
            os.unlink(tmp_path)


# EOF
