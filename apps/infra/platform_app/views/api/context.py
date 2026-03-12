"""
Unified context endpoint — one-call bootstrap for community apps.

Endpoint:
    GET /platform/api/context/

Query params:
    project_id  — scope to a specific project (optional)

Returns user profile, project metadata, and file tree in a single call.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@login_required
@require_GET
def context(request):
    """Return unified platform context for the authenticated user."""
    try:
        user = request.user
        project = _resolve_project(request)

        result = {
            "user": {
                "id": user.pk,
                "username": user.username,
                "email": user.email,
            },
        }

        if project:
            result["project"] = {
                "id": str(project.pk),
                "name": project.name,
                "slug": project.slug,
                "created_at": project.created_at.isoformat(),
            }
            result["file_tree"] = _get_file_tree(project)

        return JsonResponse({"success": True, "context": result})

    except Exception as exc:
        logger.exception("Error building context")
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


def _resolve_project(request):
    """Return Project instance or None."""
    project_id = request.GET.get("project_id") or request.session.get(
        "active_project_id"
    )
    if not project_id:
        return None

    try:
        from apps.infra.project_app.models import Project

        return Project.objects.get(pk=project_id, owner=request.user)
    except Exception:
        return None


def _get_file_tree(project):
    """Return flat file list for a project directory."""
    from pathlib import Path

    project_dir = Path(project.get_absolute_path())
    if not project_dir.is_dir():
        return []

    tree = []
    for p in sorted(project_dir.rglob("*")):
        if p.name.startswith("."):
            continue
        rel = str(p.relative_to(project_dir))
        tree.append({"path": rel, "is_dir": p.is_dir()})
    return tree


# EOF
