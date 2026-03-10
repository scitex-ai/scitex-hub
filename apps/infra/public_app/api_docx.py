#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOCX to LaTeX conversion API view.
"""

import base64
import logging
import os
import tempfile
import traceback
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger("scitex")


@csrf_exempt
@require_http_methods(["POST"])
def docx2tex_convert(request):
    """
    Convert DOCX file to LaTeX using scitex.msword.

    Accepts:
    - file: The uploaded .docx file
    - profile: Journal profile name (default: "generic")
    - link_mode: "by-number" or "by-proximity" (default: "by-number")
    - normalize_headings: bool (default: True)
    - validate: bool (default: True)
    - extract_images: bool (default: True)
    """
    try:
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file provided"}, status=400)

        uploaded_file = request.FILES["file"]

        if not uploaded_file.name.lower().endswith(".docx"):
            return JsonResponse(
                {"error": "Invalid file type. Please upload a .docx file"},
                status=400,
            )

        options = _parse_docx_options(request)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
            for chunk in uploaded_file.chunks():
                tmp_file.write(chunk)
            tmp_path = Path(tmp_file.name)

        tex_path = None
        try:
            response_data = _convert_docx_to_latex(tmp_path, options)
            tex_path = response_data.pop("_tex_path", None)
            return JsonResponse(response_data)

        finally:
            if tmp_path.exists():
                os.unlink(tmp_path)
            if tex_path and tex_path.exists():
                os.unlink(tex_path)

    except ImportError as e:
        logger.error(f"Failed to import scitex.msword: {e}")
        return JsonResponse(
            {"error": "DOCX conversion not available (scitex.msword not installed)"},
            status=500,
        )

    except Exception as e:
        logger.error(f"Error converting DOCX to LaTeX: {e}")
        traceback.print_exc()
        return JsonResponse({"error": f"Conversion failed: {str(e)}"}, status=500)


def _parse_docx_options(request) -> dict:
    """Parse DOCX conversion options from request."""
    return {
        "profile": request.POST.get("profile", "generic"),
        "link_mode": request.POST.get("link_mode", "by-number"),
        "normalize_headings": request.POST.get("normalize_headings", "true").lower()
        == "true",
        "validate": request.POST.get("validate", "true").lower() == "true",
        "extract_images": request.POST.get("extract_images", "true").lower() == "true",
    }


def _convert_docx_to_latex(tmp_path: Path, options: dict) -> dict:
    """Perform DOCX to LaTeX conversion."""
    from scitex.msword import (
        link_captions_to_images,
        link_captions_to_images_by_proximity,
        load_docx,
        normalize_section_headings,
        validate_document,
    )
    from scitex.tex import export_tex

    doc = load_docx(
        tmp_path, profile=options["profile"], extract_images=options["extract_images"]
    )

    if options["normalize_headings"]:
        doc = normalize_section_headings(doc)

    if options["extract_images"] and doc.get("images"):
        if options["link_mode"] == "by-proximity":
            doc = link_captions_to_images_by_proximity(doc)
        else:
            doc = link_captions_to_images(doc)

    if options["validate"]:
        doc = validate_document(doc)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".tex", mode="w") as tex_file:
        tex_path = Path(tex_file.name)

    with tempfile.TemporaryDirectory() as img_dir:
        tex_path = export_tex(doc, tex_path, image_dir=img_dir)
        latex_content = tex_path.read_text()

    images_response = _encode_images(doc.get("images", []))

    return {
        "latex": latex_content,
        "metadata": doc.get("metadata", {}),
        "blocks": doc.get("blocks", []),
        "images": images_response,
        "references": doc.get("references", []),
        "warnings": doc.get("warnings", []),
        "_tex_path": tex_path,
    }


def _encode_images(images: list) -> list:
    """Encode images to base64 for JSON response."""
    images_response = []
    for img in images:
        img_data = {
            "rel_id": img.get("rel_id", ""),
            "hash": img.get("hash", ""),
            "content_type": img.get("content_type", "image/png"),
            "extension": img.get("extension", ".png"),
            "size_bytes": img.get("size_bytes", 0),
        }
        if "data" in img and img["data"]:
            img_data["data"] = base64.b64encode(img["data"]).decode("utf-8")
        images_response.append(img_data)
    return images_response
