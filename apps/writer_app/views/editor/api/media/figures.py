#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Figures API views."""
from __future__ import annotations
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ...auth_utils import api_login_optional, get_user_for_request

logger = logging.getLogger(__name__)


@api_login_optional
@require_http_methods(["GET"])
def figures_api(request, project_id):
    """
    Get all figures from project SQLite DB (fast!).

    Query params:
        - source: 'paper', 'pool', 'data', 'scripts', 'all' (default: 'all')
        - is_referenced: 'true', 'false', 'all' (default: 'all')
        - file_type: 'png', 'pdf', 'jpg', etc. or 'all' (default: 'all')
        - q: search query (full-text search)

    Returns:
        JSON with:
            - success: bool
            - figures: list of figure dictionaries
            - stats: {total, referenced, sources, total_size}
    """
    try:
        from apps.project_app.models import Project
        from .....utils.project_db import get_project_db

        project = Project.objects.get(id=project_id)
        user, is_visitor = get_user_for_request(request, project_id)

        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        db = get_project_db(project)

        # Parse filters
        filters = {}
        if request.GET.get('source') and request.GET.get('source') != 'all':
            filters['source'] = request.GET.get('source')

        if request.GET.get('is_referenced') and request.GET.get('is_referenced') != 'all':
            filters['is_referenced'] = request.GET.get('is_referenced') == 'true'

        if request.GET.get('file_type') and request.GET.get('file_type') != 'all':
            filters['file_type'] = request.GET.get('file_type')

        # Search or filter
        search_query = request.GET.get('q')
        if search_query:
            figures = db.search_figures(search_query)
        else:
            figures = db.get_all_figures(filters)

        # Get stats
        stats = db.get_stats()

        # Convert thumbnail paths to URLs
        for fig in figures:
            if fig.get('thumbnail_path'):
                # Serve from project's scitex/thumbnails/
                from pathlib import Path
                thumb_name = Path(fig['thumbnail_path']).name
                fig['thumbnail_url'] = f"/writer/api/project/{project_id}/thumbnail/{thumb_name}"
            else:
                fig['thumbnail_url'] = '/static/images/thumbnail_placeholder.png'

        logger.info(f"[Figures API] Returned {len(figures)} figures for project {project_id}")

        return JsonResponse({
            'success': True,
            'figures': figures,
            'stats': stats,
        })

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[Figures API] Error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_login_optional
@require_http_methods(["POST"])
def refresh_figures_index(request, project_id):
    """
    Trigger background re-indexing of figures.

    This starts an asynchronous task to scan the project and update
    the metadata database.

    Returns:
        JSON with success status
    """
    try:
        from apps.project_app.models import Project
        from .....tasks.indexer import index_project_figures, CELERY_AVAILABLE

        project = Project.objects.get(id=project_id)
        user, is_visitor = get_user_for_request(request, project_id)

        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        # Trigger background indexing
        if CELERY_AVAILABLE:
            index_project_figures.delay(project_id)
        else:
            # Call directly if Celery not available (dev mode)
            index_project_figures(project_id)

        logger.info(f"[Figures API] Triggered re-indexing for project {project_id}")

        return JsonResponse({
            'success': True,
            'message': 'Indexing started in background'
        })

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[Figures API] Error triggering refresh: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_login_optional
@require_http_methods(["POST"])
def upload_figures(request, project_id):
    """
    Upload figure files to scitex/writer/uploads/figures/.

    Accepts multipart/form-data with files array.
    After upload, triggers indexing task.

    Returns:
        JSON with success status and list of uploaded files
    """
    try:
        from apps.project_app.models import Project
        from pathlib import Path
        from .....tasks.indexer import index_project_figures, CELERY_AVAILABLE

        project = Project.objects.get(id=project_id)
        user, is_visitor = get_user_for_request(request, project_id)

        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        # Get uploaded files
        files = request.FILES.getlist('files')
        if not files:
            return JsonResponse(
                {"success": False, "error": "No files provided"}, status=400
            )

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

        # Create upload directory: scitex/writer/uploads/figures/
        upload_dir = project_path / 'scitex' / 'writer' / 'uploads' / 'figures'
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Save files
        uploaded_files = []
        for uploaded_file in files:
            file_path = upload_dir / uploaded_file.name

            # Write file in chunks
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            uploaded_files.append({
                'name': uploaded_file.name,
                'size': uploaded_file.size,
                'path': str(file_path.relative_to(project_path))
            })

            logger.info(f"[Upload] Saved figure: {uploaded_file.name} ({uploaded_file.size} bytes)")

        # Trigger indexing
        if CELERY_AVAILABLE:
            index_project_figures.delay(project_id)
        else:
            index_project_figures(project_id)

        logger.info(f"[Upload] Uploaded {len(uploaded_files)} figures for project {project_id}")

        return JsonResponse({
            'success': True,
            'files': uploaded_files,
            'message': f'Successfully uploaded {len(uploaded_files)} file(s)'
        })

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[Upload] Error uploading figures: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# EOF
