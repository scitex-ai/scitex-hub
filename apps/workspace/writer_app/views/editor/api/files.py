#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-hub/apps/writer_app/views/editor/api/files.py
"""File operations - PDF serving, thumbnails, SyncTeX reverse lookup."""

from __future__ import annotations

import logging
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.platform_app.services.paths import is_within, resolve_within
from apps.security import safe_log_field

from ..auth_utils import api_login_optional, get_user_for_request

logger = logging.getLogger(__name__)

FULL_DOCUMENT_PDF_DIRS = {
    "manuscript.pdf": "01_manuscript",
    "supplementary.pdf": "02_supplementary",
    "revision.pdf": "03_revision",
}


def writer_pdf_candidates(writer_dir: Path, pdf_filename: str) -> list[Path]:
    """Locations a Writer PDF may live in, most specific first."""
    candidates = []
    preview = resolve_within(writer_dir, ".preview")
    candidate = resolve_within(preview, pdf_filename) if preview is not None else None
    if candidate is not None:
        candidates.append(candidate)
    if pdf_filename in FULL_DOCUMENT_PDF_DIRS:
        document_dir = resolve_within(writer_dir, FULL_DOCUMENT_PDF_DIRS[pdf_filename])
        candidate = (
            resolve_within(document_dir, pdf_filename)
            if document_dir is not None
            else None
        )
        if candidate is not None:
            candidates.append(candidate)
    output_dir = resolve_within(writer_dir, "preview_output")
    candidate = (
        resolve_within(output_dir, pdf_filename) if output_dir is not None else None
    )
    if candidate is not None:
        candidates.append(candidate)
    return candidates


def find_writer_pdf(writer_dir: Path, pdf_filename: str) -> Path | None:
    """First existing Writer PDF named ``pdf_filename``, or None."""
    return next(
        (
            path
            for path in writer_pdf_candidates(writer_dir, pdf_filename)
            if path.exists()
        ),
        None,
    )


@api_login_optional
@require_http_methods(["GET", "HEAD"])
def pdf_view(request, project_id, pdf_filename=None):
    """Serve PDF files from project's .preview directory.

    Supports both GET (download PDF) and HEAD (check if PDF exists) requests.

    Args:
        project_id: Project ID
        pdf_filename: PDF filename (e.g., 'preview-abstract.pdf')
    """
    try:
        from apps.infra.project_app.models import Project

        from ....services import WriterService

        # Get effective user (authenticated or visitor)
        user, is_visitor = get_user_for_request(request, project_id)
        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        # Get project
        Project.objects.get(id=project_id)
        writer_service = WriterService(project_id, user.id)

        # Handle doc_type query parameter (for compiled full manuscripts)
        doc_type = request.GET.get("doc_type")
        if doc_type and not pdf_filename:
            # Map doc_type to PDF filename
            doc_type_map = {
                "manuscript": "manuscript.pdf",
                "supplementary": "supplementary.pdf",
                "revision": "revision.pdf",
            }
            pdf_filename = doc_type_map.get(doc_type, "manuscript.pdf")
            logger.info(
                "[PDFView] Mapped doc_type=%s to filename=%s",
                safe_log_field(doc_type),
                safe_log_field(pdf_filename),
            )

        # If no filename specified, look for main compiled PDF
        if not pdf_filename:
            pdf_filename = "main.pdf"

        logger.info(
            "[PDFView] Serving PDF=%s for project=%s",
            safe_log_field(pdf_filename),
            safe_log_field(project_id),
        )

        checked_paths = writer_pdf_candidates(writer_service.writer_dir, pdf_filename)
        pdf_path = find_writer_pdf(writer_service.writer_dir, pdf_filename)

        if not pdf_path:
            logger.error("[PDFView] PDF not found: %s", safe_log_field(pdf_filename))
            logger.error(
                "[PDFView] Checked paths: %s", safe_log_field(checked_paths)
            )
            # For HEAD requests, return simple 404 without JSON body
            if request.method == "HEAD":
                return HttpResponse(status=404)
            return JsonResponse(
                {"success": False, "error": f"PDF not found: {pdf_filename}"},
                status=404,
            )

        logger.info("[PDFView] Serving PDF from: %s", safe_log_field(pdf_path))

        # For HEAD requests, just return 200 OK without file content
        if request.method == "HEAD":
            response = HttpResponse(status=200)
            response["Content-Type"] = "application/pdf"
            response["Content-Disposition"] = f'inline; filename="{pdf_filename}"'
            return response

        # For GET requests, serve the PDF file
        response = FileResponse(open(pdf_path, "rb"), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{pdf_filename}"'

        # Add cache control headers to prevent browser caching themed PDFs
        # This is critical for theme switching to work correctly
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"

        return response

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception:
        logger.exception("Error serving PDF for project %s", safe_log_field(project_id))
        return JsonResponse({"success": False, "error": "Unable to serve PDF."}, status=500)


@login_required
@require_http_methods(["GET"])
def presence_list_view(request, project_id):
    """Get list of active users in a project.

    Args:
        project_id: Project ID from URL

    Returns:
        JSON with list of active users and their cursor positions
    """
    try:
        # TODO: Implement proper presence tracking with Redis/Django Channels
        # For now, return empty list to avoid 500 errors
        return JsonResponse(
            {
                "success": True,
                "users": [],
                "message": "Presence tracking not yet implemented",
            }
        )

    except Exception:
        logger.exception("Error getting presence list for %s", safe_log_field(project_id))
        return JsonResponse({"success": False, "error": "Unable to list presence."}, status=500)


@require_http_methods(["GET"])
def thumbnail_view(request, project_id, thumbnail_name):
    """
    Serve thumbnail from scitex/thumbnails/.

    Note: This endpoint does not require authentication because:
    1. The thumbnail filename itself is a secure hash (acts as a token)
    2. Browser <img> tags don't send session cookies
    3. Thumbnails contain no sensitive information

    Args:
        project_id: Project ID
        thumbnail_name: Thumbnail filename

    Returns:
        FileResponse with JPEG image or placeholder
    """
    try:
        from pathlib import Path

        from django.conf import settings

        from apps.infra.project_app.models import Project

        project = Project.objects.get(id=project_id)

        # Get project path
        if hasattr(project, "git_clone_path") and project.git_clone_path:
            project_path = Path(project.git_clone_path)
        else:
            from apps.infra.project_app.services.project_filesystem import (
                get_project_filesystem_manager,
            )

            if not hasattr(project, "owner") or not project.owner:
                raise ValueError("Cannot determine project owner")
            manager = get_project_filesystem_manager(project.owner)
            project_path = manager.get_project_root_path(project)
            if not project_path:
                raise ValueError(f"Project path not found for project {project.id}")

        thumbnails = resolve_within(project_path, "scitex/thumbnails")
        thumb_path = (
            resolve_within(thumbnails, thumbnail_name)
            if thumbnails is not None
            else None
        )

        if thumb_path is not None and thumb_path.exists():
            return FileResponse(open(thumb_path, "rb"), content_type="image/jpeg")
        else:
            # Return placeholder
            placeholder = (
                Path(settings.STATIC_ROOT) / "images" / "thumbnail_placeholder.png"
            )
            if placeholder.exists():
                return FileResponse(open(placeholder, "rb"), content_type="image/png")
            else:
                return JsonResponse(
                    {"success": False, "error": "Thumbnail not found"}, status=404
                )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception:
        logger.exception(
            "[Thumbnail] Error serving %s", safe_log_field(thumbnail_name)
        )
        return JsonResponse({"success": False, "error": "Unable to serve thumbnail."}, status=500)


@api_login_optional
@require_http_methods(["POST"])
def synctex_reverse_lookup(request, project_id):
    """SyncTeX reverse lookup: PDF (page, x, y) -> .tex (file, line).

    Accepts click coordinates from the PDF viewer and returns the
    corresponding .tex source file and line number using the synctex
    command-line tool.

    POST body:
        {
            "page": 1,
            "x": 150.5,
            "y": 400.2,
            "pdf_filename": "manuscript.pdf"
        }

    Returns:
        {
            "success": true,
            "file": "01_manuscript/contents/introduction.tex",
            "line": 42,
            "column": 0
        }
    """
    import json
    import re
    import subprocess
    from pathlib import Path

    try:
        from apps.infra.project_app.models import Project

        from ....services import WriterService

        # Get effective user (authenticated or visitor)
        user, is_visitor = get_user_for_request(request, project_id)
        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        data = json.loads(request.body)
        page = data.get("page")
        x = data.get("x")
        y = data.get("y")
        pdf_filename = data.get("pdf_filename", "manuscript.pdf")

        if page is None or x is None or y is None:
            return JsonResponse(
                {"success": False, "error": "page, x, and y are required"},
                status=400,
            )

        # Get project and writer service
        Project.objects.get(id=project_id)
        writer_service = WriterService(project_id, user.id)
        writer_dir = writer_service.writer_dir

        # Locate the PDF and its .synctex.gz file
        pdf_path = None
        search_locations = []

        # Full manuscript PDFs in document type directories
        doc_type_dirs = {
            "manuscript.pdf": "01_manuscript",
            "supplementary.pdf": "02_supplementary",
            "revision.pdf": "03_revision",
        }

        doc_dir_name = doc_type_dirs.get(pdf_filename)
        if doc_dir_name:
            document_dir = resolve_within(writer_dir, doc_dir_name)
            candidate = (
                resolve_within(document_dir, pdf_filename)
                if document_dir is not None
                else None
            )
            if candidate is not None:
                search_locations.append(candidate)
            if candidate is not None and candidate.exists():
                pdf_path = candidate

        # Also check logs directory where latexmk outputs
        if not pdf_path and doc_dir_name:
            logs_dir = resolve_within(writer_dir, f"{doc_dir_name}/logs")
            if logs_dir is not None and logs_dir.exists():
                candidate = resolve_within(logs_dir, pdf_filename)
                if candidate is not None:
                    search_locations.append(candidate)
                if candidate is not None and candidate.exists():
                    pdf_path = candidate

        # Preview directory
        if not pdf_path:
            preview_dir = resolve_within(writer_dir, ".preview")
            candidate = (
                resolve_within(preview_dir, pdf_filename)
                if preview_dir is not None
                else None
            )
            if candidate is not None:
                search_locations.append(candidate)
            if candidate is not None and candidate.exists():
                pdf_path = candidate

        if not pdf_path:
            logger.error(
                "[SyncTeX] PDF not found=%s checked=%s",
                safe_log_field(pdf_filename),
                safe_log_field([str(p) for p in search_locations]),
            )
            return JsonResponse(
                {"success": False, "error": f"PDF not found: {pdf_filename}"},
                status=404,
            )

        # Find .synctex.gz file near the PDF
        synctex_gz = pdf_path.with_suffix(".synctex.gz")
        synctex_plain = pdf_path.with_suffix(".synctex")

        # Also check logs directory for synctex file
        if not synctex_gz.exists() and not synctex_plain.exists() and doc_dir_name:
            logs_dir = resolve_within(writer_dir, f"{doc_dir_name}/logs")
            if logs_dir is None:
                return JsonResponse(
                    {"success": False, "error": "Invalid SyncTeX path."}, status=400
                )
            synctex_gz = resolve_within(logs_dir, pdf_path.stem + ".synctex.gz")
            synctex_plain = resolve_within(logs_dir, pdf_path.stem + ".synctex")
            if synctex_gz is None or synctex_plain is None:
                return JsonResponse(
                    {"success": False, "error": "Invalid SyncTeX path."}, status=400
                )

        if not synctex_gz.exists() and not synctex_plain.exists():
            logger.warning(
                "[SyncTeX] No data for %s. Checked: %s, %s",
                safe_log_field(pdf_filename),
                safe_log_field(synctex_gz),
                safe_log_field(synctex_plain),
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": "SyncTeX data not found. Recompile with SyncTeX enabled.",
                },
                status=404,
            )

        # Run synctex edit command
        # synctex edit -o "page:x:y:file.pdf"
        synctex_query = f"{page}:{x}:{y}:{pdf_path}"
        logger.info('[SyncTeX] Running query "%s"', safe_log_field(synctex_query))

        result = subprocess.run(
            ["synctex", "edit", "-o", synctex_query],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(writer_dir),
        )

        logger.info("[SyncTeX] stdout: %s", safe_log_field(result.stdout))
        if result.stderr:
            logger.warning("[SyncTeX] stderr: %s", safe_log_field(result.stderr))

        if result.returncode != 0:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"synctex command failed (exit {result.returncode})",
                },
                status=500,
            )

        # Parse synctex output
        # Format:
        #   Input:<filepath>
        #   Line:<line_number>
        #   Column:<column_number>
        output = result.stdout
        input_match = re.search(r"Input:(.+)", output)
        line_match = re.search(r"Line:(\d+)", output)
        column_match = re.search(r"Column:(-?\d+)", output)

        if not input_match or not line_match:
            logger.warning("[SyncTeX] Could not parse output: %s", safe_log_field(output))
            return JsonResponse(
                {
                    "success": False,
                    "error": "SyncTeX returned no match for this position",
                },
                status=200,
            )

        source_file = input_match.group(1).strip()
        source_line = int(line_match.group(1))
        source_column = int(column_match.group(1)) if column_match else 0

        # Make path relative to writer_dir for the frontend
        source_path = Path(source_file)
        try:
            relative_path = source_path.relative_to(writer_dir)
        except ValueError:
            return JsonResponse(
                {"success": False, "error": "SyncTeX returned an invalid source path."},
                status=500,
            )
        if not is_within(writer_dir, source_path):
            return JsonResponse(
                {"success": False, "error": "SyncTeX returned an invalid source path."},
                status=500,
            )

        logger.info(
            "[SyncTeX] Result: %s:%s:%s",
            safe_log_field(relative_path),
            safe_log_field(source_line),
            safe_log_field(source_column),
        )

        return JsonResponse(
            {
                "success": True,
                "file": str(relative_path),
                "line": source_line,
                "column": max(0, source_column),
            }
        )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except subprocess.TimeoutExpired:
        return JsonResponse(
            {"success": False, "error": "SyncTeX lookup timed out"}, status=500
        )
    except Exception:
        logger.exception("[SyncTeX] Error for project %s", safe_log_field(project_id))
        return JsonResponse({"success": False, "error": "SyncTeX lookup failed."}, status=500)


# EOF
