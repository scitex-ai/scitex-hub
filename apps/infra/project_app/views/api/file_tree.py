"""
File Tree API Views

API endpoints for project file tree navigation.
"""

from __future__ import annotations

import logging

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from ...models import Project
from ...services.file_tree_builder import build_project_file_tree

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def api_file_tree(request, username, slug):
    """API endpoint to get project file tree for sidebar navigation"""
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Public projects are readable by anyone; private projects require an
    # authenticated owner/collaborator. Session keys never confer identity.
    has_access = project.visibility == "public" or (
        request.user.is_authenticated
        and (
            project.owner == request.user
            or project.collaborators.filter(id=request.user.id).exists()
        )
    )

    if not has_access:
        return JsonResponse({"success": False, "error": "Permission denied"})

    result = build_project_file_tree(project)
    if result is None:
        return JsonResponse({"success": False, "error": "Project directory not found"})

    # API returns {"success": True, "tree": [...]} format
    return JsonResponse({"success": True, "tree": result["treeData"]})


# EOF
