#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/views/editor/api/files.py
"""File operations - PDF serving, thumbnails."""

from __future__ import annotations
import logging
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from ..auth_utils import api_login_optional, get_user_for_request

logger = logging.getLogger(__name__)


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
        from ....services import WriterService
        from apps.project_app.models import Project

        # Get effective user (authenticated or visitor)
        user, is_visitor = get_user_for_request(request, project_id)
        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        # Get project
        project = Project.objects.get(id=project_id)
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
                f"[PDFView] Mapped doc_type={doc_type} to filename={pdf_filename}"
            )

        # If no filename specified, look for main compiled PDF
        if not pdf_filename:
            pdf_filename = "main.pdf"

        logger.info(f"[PDFView] Serving PDF: {pdf_filename} for project {project_id}")

        # Search for PDF in multiple locations
        writer_dir = writer_service.writer_dir  # Already at scitex/writer/
        pdf_path = None
        checked_paths = []

        # 1. Preview directory (for section previews)
        preview_dir = writer_dir / ".preview"
        preview_path = preview_dir / pdf_filename
        checked_paths.append(str(preview_path))
        if preview_path.exists():
            pdf_path = preview_path
            logger.info(f"[PDFView] Found PDF in .preview directory")

        # 2. Full manuscript PDFs in document type directories
        if not pdf_path and pdf_filename in [
            "manuscript.pdf",
            "supplementary.pdf",
            "revision.pdf",
        ]:
            doc_type_map = {
                "manuscript.pdf": "01_manuscript",
                "supplementary.pdf": "02_supplementary",
                "revision.pdf": "03_revision",
            }
            doc_dir = doc_type_map.get(pdf_filename)
            if doc_dir:
                full_path = writer_dir / doc_dir / pdf_filename
                checked_paths.append(str(full_path))
                if full_path.exists():
                    pdf_path = full_path
                    logger.info(f"[PDFView] Found full PDF in {doc_dir} directory")

        # 3. Fallback to old preview_output directory for backward compatibility
        if not pdf_path:
            legacy_preview = writer_service.writer_dir / "preview_output" / pdf_filename
            checked_paths.append(str(legacy_preview))
            if legacy_preview.exists():
                pdf_path = legacy_preview
                logger.info(f"[PDFView] Found PDF in legacy preview_output directory")

        # If still not found, return 404
        if not pdf_path:
            logger.error(f"[PDFView] PDF not found: {pdf_filename}")
            logger.error(f"[PDFView] Checked paths: {', '.join(checked_paths)}")
            # For HEAD requests, return simple 404 without JSON body
            if request.method == "HEAD":
                return HttpResponse(status=404)
            return JsonResponse(
                {"success": False, "error": f"PDF not found: {pdf_filename}"},
                status=404,
            )

        logger.info(f"[PDFView] Serving PDF from: {pdf_path}")

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
    except Exception as e:
        logger.error(f"Error serving PDF: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


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

    except Exception as e:
        logger.error(f"Error getting presence list: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


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
        from django.conf import settings
        from apps.project_app.models import Project
        from pathlib import Path

        project = Project.objects.get(id=project_id)

        # Get project path
        if hasattr(project, 'git_clone_path') and project.git_clone_path:
            project_path = Path(project.git_clone_path)
        else:
            from apps.project_app.services.project_filesystem import get_project_filesystem_manager
            if not hasattr(project, 'owner') or not project.owner:
                raise ValueError("Cannot determine project owner")
            manager = get_project_filesystem_manager(project.owner)
            project_path = manager.get_project_root_path(project)
            if not project_path:
                raise ValueError(f"Project path not found for project {project.id}")

        thumb_path = project_path / 'scitex' / 'thumbnails' / thumbnail_name

        if thumb_path.exists():
            return FileResponse(open(thumb_path, 'rb'), content_type='image/jpeg')
        else:
            # Return placeholder
            placeholder = Path(settings.STATIC_ROOT) / 'images' / 'thumbnail_placeholder.png'
            if placeholder.exists():
                return FileResponse(open(placeholder, 'rb'), content_type='image/png')
            else:
                return JsonResponse(
                    {"success": False, "error": "Thumbnail not found"}, status=404
                )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[Thumbnail] Error serving {thumbnail_name}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# EOF
