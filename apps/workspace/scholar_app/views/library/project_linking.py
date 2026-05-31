#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Linking Views for Scholar Library

API endpoints for linking papers from user library to research projects.
"""

import json
import logging
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ...models import UserLibrary
from ...services import ProjectLibraryLinker

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def api_link_paper_to_project(request, paper_id):
    """
    Link a paper from user library to a project.

    POST /api/library/papers/<paper_id>/link/
    Body: {"project_id": "uuid"}

    Request:
        paper_id (UUID): UserLibrary entry ID
        project_id (UUID): Project ID to link to

    Returns:
        JSON response: {
            "success": bool,
            "symlink_created": bool,
            "bibtex_synced": bool,
            "message": str
        }

    Error codes:
        400: Invalid request body or paper not in user library
        403: Permission denied (not project owner)
        404: Paper or project not found
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        project_id = data.get("project_id")

        if not project_id:
            return JsonResponse(
                {"success": False, "error": "project_id is required"}, status=400
            )

        # Get UserLibrary entry
        try:
            paper_id = UUID(str(paper_id))
            user_library_entry = UserLibrary.objects.select_related("paper").get(
                id=paper_id, user=request.user
            )
        except UserLibrary.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Paper not found in your library"},
                status=404,
            )

        # Get Project
        from apps.infra.project_app.models import Project

        try:
            project_id = UUID(str(project_id))
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Project not found"}, status=404
            )

        # Verify user has access to project
        if project.owner != request.user:
            # TODO: Check if user is collaborator with write access
            return JsonResponse(
                {
                    "success": False,
                    "error": "You do not have permission to link papers to this project",
                },
                status=403,
            )

        # Link paper to project
        linker = ProjectLibraryLinker(request.user)
        result = linker.link_paper_to_project(user_library_entry, project)

        status_code = 200 if result["success"] else 500
        return JsonResponse(result, status=status_code)

    except ValueError as e:
        logger.error(f"Validation error linking paper: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error linking paper: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "error": "Internal server error"}, status=500
        )


@login_required
@require_http_methods(["POST"])
def api_unlink_paper_from_project(request, paper_id):
    """
    Unlink a paper from its project.

    POST /api/library/papers/<paper_id>/unlink/

    Request:
        paper_id (UUID): UserLibrary entry ID

    Returns:
        JSON response: {
            "success": bool,
            "symlink_removed": bool,
            "bibtex_synced": bool,
            "message": str
        }

    Error codes:
        400: Paper not linked to a project
        403: Permission denied
        404: Paper not found
    """
    try:
        # Get UserLibrary entry
        try:
            paper_id = UUID(str(paper_id))
            user_library_entry = UserLibrary.objects.select_related(
                "paper", "project"
            ).get(id=paper_id, user=request.user)
        except UserLibrary.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Paper not found in your library"},
                status=404,
            )

        # Check if paper is linked to a project
        if not user_library_entry.project:
            return JsonResponse(
                {"success": False, "error": "Paper is not linked to any project"},
                status=400,
            )

        project = user_library_entry.project

        # Verify user has access to project
        if project.owner != request.user:
            # TODO: Check if user is collaborator with write access
            return JsonResponse(
                {
                    "success": False,
                    "error": "You do not have permission to unlink papers from this project",
                },
                status=403,
            )

        # Unlink paper from project
        linker = ProjectLibraryLinker(request.user)
        result = linker.unlink_paper_from_project(user_library_entry, project)

        status_code = 200 if result["success"] else 500
        return JsonResponse(result, status=status_code)

    except ValueError as e:
        logger.error(f"Validation error unlinking paper: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error unlinking paper: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "error": "Internal server error"}, status=500
        )


@login_required
@require_http_methods(["GET"])
def api_project_papers(request, project_id):
    """
    Get all papers linked to a project.

    GET /api/library/projects/<project_id>/papers/

    Request:
        project_id (UUID): Project ID

    Returns:
        JSON response: {
            "success": bool,
            "papers": List[dict],
            "total": int,
            "project": {
                "id": str,
                "name": str,
                "slug": str
            }
        }

    Error codes:
        403: Permission denied
        404: Project not found
    """
    try:
        # Get Project
        from apps.infra.project_app.models import Project

        try:
            project_id = UUID(str(project_id))
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Project not found"}, status=404
            )

        # Verify user has access to project
        if project.owner != request.user:
            # TODO: Check if user is collaborator with read access
            return JsonResponse(
                {
                    "success": False,
                    "error": "You do not have permission to view this project",
                },
                status=403,
            )

        # Get papers linked to project
        linker = ProjectLibraryLinker(request.user)
        entries = linker.get_project_papers(project)

        # Serialize papers
        papers = []
        for entry in entries:
            p = entry.paper
            papers.append(
                {
                    "id": str(entry.id),
                    "paper_id": str(p.id) if p else None,
                    "title": p.title if p else "Unknown",
                    "doi": p.doi if p else None,
                    "pmid": p.pmid if p else None,
                    "arxiv_id": p.arxiv_id if p else None,
                    "journal": str(p.journal) if p and p.journal else None,
                    "year": (
                        p.publication_date.year if p and p.publication_date else None
                    ),
                    "abstract": p.abstract if p and hasattr(p, "abstract") else None,
                    "reading_status": entry.reading_status,
                    "importance_rating": entry.importance_rating,
                    "personal_notes": entry.personal_notes,
                    "tags": entry.tags,
                    "saved_at": entry.saved_at.isoformat() if entry.saved_at else None,
                    "pdf_path": (
                        str(entry.user_library_pdf_path)
                        if entry.user_library_pdf_path
                        else None
                    ),
                }
            )

        return JsonResponse(
            {
                "success": True,
                "papers": papers,
                "total": len(papers),
                "project": {
                    "id": str(project.id),
                    "name": project.name,
                    "slug": project.slug,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error fetching project papers: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "error": "Internal server error"}, status=500
        )


@login_required
@require_http_methods(["POST"])
def api_setup_project_workspace(request, project_id):
    """Ensure scholar workspace exists for a project.

    POST /api/library/projects/<project_id>/setup-workspace/

    Returns workspace paths for display in the UI.
    """
    try:
        from apps.infra.project_app.models import Project

        project_id = UUID(str(project_id))
        try:
            project = Project.objects.get(id=project_id, owner=request.user)
        except Project.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Project not found"}, status=404
            )

        linker = ProjectLibraryLinker(request.user)
        paths = linker.setup_project_workspace(project)
        return JsonResponse({"success": True, **paths})

    except Exception as e:
        logger.error(f"Error setting up project workspace: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
