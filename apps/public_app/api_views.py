#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-12-11 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/api_views.py
# ----------------------------------------
"""
API views for public_app tools.

Provides backend functionality for browser-based tools that require
server-side processing.
"""

import base64
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger("scitex")

# ----------------------------------------


@csrf_exempt
@require_http_methods(["POST"])
def read_image_metadata(request):
    """
    Read embedded metadata and file info from uploaded image or PDF file.

    Supports PNG, JPEG, and PDF files. Uses scitex.io unified interface.
    Extracts:
    - Embedded metadata (from PNG tEXt chunks, JPEG EXIF, or PDF Subject field)
    - File dimensions (pixels for images, points for PDFs)
    - Page count (for PDFs)

    Returns:
        JSON response with metadata, dimensions, and file info
    """
    try:
        # Check if file was uploaded
        if "image" not in request.FILES:
            return JsonResponse(
                {"error": "No file provided", "has_metadata": False}, status=400
            )

        uploaded_file = request.FILES["image"]
        file_ext = uploaded_file.name.split('.')[-1].lower()

        # Save to temporary file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{file_ext}"
        ) as tmp_file:
            for chunk in uploaded_file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        try:
            # Import scitex.io
            from scitex.io import load, read_metadata

            # Determine file type
            is_pdf = file_ext == 'pdf'

            # Extract metadata using scitex.io
            metadata = read_metadata(tmp_path)

            # Load file to get dimensions
            if is_pdf:
                # For PDFs, load with metadata mode to get page info
                pdf_data = load(tmp_path, mode='metadata')

                response_data = {
                    "has_metadata": metadata is not None,
                    "metadata": metadata,
                    "file_type": "pdf",
                    "page_count": pdf_data.get('pages', 0),
                    "dimensions": {
                        "width_pt": None,  # Need first page for this
                        "height_pt": None,
                        "pages": pdf_data.get('pages', 0),
                    },
                    "pdf_metadata": {
                        "title": pdf_data.get('title', ''),
                        "author": pdf_data.get('author', ''),
                        "subject": pdf_data.get('subject', ''),
                        "creator": pdf_data.get('creator', ''),
                    }
                }
            else:
                # For images, load to get dimensions
                img, _ = load(tmp_path, metadata=True)

                response_data = {
                    "has_metadata": metadata is not None,
                    "metadata": metadata,
                    "file_type": "image",
                    "dimensions": {
                        "width": img.width,
                        "height": img.height,
                    }
                }

                img.close()

            if metadata is None:
                response_data["message"] = f"No scitex metadata found in {file_ext.upper()}"
            else:
                response_data["message"] = "Metadata successfully extracted"

            return JsonResponse(response_data)

        finally:
            # Clean up temporary file
            import os

            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

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

    Returns:
        JSON response with:
        - latex: The generated LaTeX content
        - metadata: Document metadata
        - blocks: Document structure blocks
        - images: Extracted images (base64 encoded if extract_images=True)
        - references: Parsed references
        - warnings: Document validation warnings
    """
    try:
        # Check if file was uploaded
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file provided"}, status=400)

        uploaded_file = request.FILES["file"]

        # Validate file extension
        if not uploaded_file.name.lower().endswith(".docx"):
            return JsonResponse(
                {"error": "Invalid file type. Please upload a .docx file"},
                status=400,
            )

        # Parse options from form data
        profile = request.POST.get("profile", "generic")
        link_mode = request.POST.get("link_mode", "by-number")
        normalize_headings = request.POST.get("normalize_headings", "true").lower() == "true"
        validate = request.POST.get("validate", "true").lower() == "true"
        extract_images = request.POST.get("extract_images", "true").lower() == "true"

        # Save to temporary file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".docx"
        ) as tmp_file:
            for chunk in uploaded_file.chunks():
                tmp_file.write(chunk)
            tmp_path = Path(tmp_file.name)

        try:
            # Import scitex.msword
            from scitex.msword import (
                load_docx,
                normalize_section_headings,
                link_captions_to_images,
                link_captions_to_images_by_proximity,
                validate_document,
            )
            from scitex.tex import export_tex

            # 1. Load DOCX
            doc = load_docx(tmp_path, profile=profile, extract_images=extract_images)

            # 2. Normalize headings (optional)
            if normalize_headings:
                doc = normalize_section_headings(doc)

            # 3. Link captions to images (optional)
            if extract_images and doc.get("images"):
                if link_mode == "by-proximity":
                    doc = link_captions_to_images_by_proximity(doc)
                else:
                    doc = link_captions_to_images(doc)

            # 4. Validate document (optional)
            if validate:
                doc = validate_document(doc)

            # 5. Export to LaTeX
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".tex", mode="w"
            ) as tex_file:
                tex_path = Path(tex_file.name)

            # Create temp directory for images
            with tempfile.TemporaryDirectory() as img_dir:
                tex_path = export_tex(doc, tex_path, image_dir=img_dir)

                # Read the generated LaTeX
                latex_content = tex_path.read_text()

            # Prepare images for JSON response (base64 encode)
            images_response = []
            for img in doc.get("images", []):
                img_data = {
                    "rel_id": img.get("rel_id", ""),
                    "hash": img.get("hash", ""),
                    "content_type": img.get("content_type", "image/png"),
                    "extension": img.get("extension", ".png"),
                    "size_bytes": img.get("size_bytes", 0),
                }
                # Include base64 data if available
                if "data" in img and img["data"]:
                    img_data["data"] = base64.b64encode(img["data"]).decode("utf-8")
                images_response.append(img_data)

            # Build response
            response_data = {
                "latex": latex_content,
                "metadata": doc.get("metadata", {}),
                "blocks": doc.get("blocks", []),
                "images": images_response,
                "references": doc.get("references", []),
                "warnings": doc.get("warnings", []),
            }

            return JsonResponse(response_data)

        finally:
            # Clean up temporary files
            import os

            if tmp_path.exists():
                os.unlink(tmp_path)
            if tex_path.exists():
                os.unlink(tex_path)

    except ImportError as e:
        logger.error(f"Failed to import scitex.msword: {e}")
        return JsonResponse(
            {"error": "DOCX conversion not available (scitex.msword not installed)"},
            status=500,
        )

    except Exception as e:
        logger.error(f"Error converting DOCX to LaTeX: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {"error": f"Conversion failed: {str(e)}"},
            status=500,
        )


# EOF
