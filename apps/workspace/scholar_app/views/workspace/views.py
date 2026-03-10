"""Default workspace views for Scholar app."""

import logging

from django.shortcuts import render

from apps.infra.project_app.services.anonymous_storage import get_visitor_storage_path

logger = logging.getLogger(__name__)


def guest_session_view(request, username):
    """Guest session workspace for Scholar - supports visitor users."""
    # Handle visitor users
    is_anon = not request.user.is_authenticated

    if is_anon:
        # Ensure session exists for anonymous users
        if not request.session.session_key:
            request.session.create()

        # Get temporary storage path
        storage_path = get_visitor_storage_path(request.session.session_key)
        display_username = f"guest-{request.session.session_key[:8]}"
    else:
        storage_path = f"/data/users/{request.user.username}/proj/"
        display_username = request.user.username

    context = {
        "is_guest_session": True,
        "guest_username": username,
        # is_visitor handled by context processor
        "storage_path": storage_path,
        "display_username": display_username,
        "module_name": "Scholar",
        "module_icon": "fa-search",
        "show_save_prompt": is_anon,
    }
    return render(request, "scholar_app/default_workspace.html", context)


def user_default_workspace(request):
    """Default workspace for logged-in users without a specific project."""
    # Support visitor users accessing this endpoint
    is_anon = not request.user.is_authenticated

    if is_anon:
        # Ensure session exists for anonymous users
        if not request.session.session_key:
            request.session.create()

        # Get temporary storage path
        storage_path = get_visitor_storage_path(request.session.session_key)
        username = None
        display_username = f"guest-{request.session.session_key[:8]}"
    else:
        storage_path = f"/data/users/{request.user.username}/proj/"
        username = request.user.username
        display_username = username

    context = {
        "is_guest_session": False,
        # is_visitor handled by context processor
        "username": username,
        "display_username": display_username,
        "storage_path": storage_path,
        "module_name": "Scholar",
        "module_icon": "fa-search",
        "show_save_prompt": is_anon,
    }
    return render(request, "scholar_app/default_workspace.html", context)


def initialize_scholar_workspace(request):
    """Initialize Scholar workspace for a project.

    POST body: {"project_id": <int>}
    """
    import json

    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "error": "Login required"}, status=403)

    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")
        if not project_id:
            return JsonResponse(
                {"success": False, "error": "project_id required"}, status=400
            )

        from apps.infra.project_app.models import Project
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        project = Project.objects.get(id=project_id, owner=request.user)
        manager = get_project_filesystem_manager(request.user)
        project_root = manager.get_project_root_path(project)

        if not project_root:
            return JsonResponse(
                {"success": False, "error": "Project directory not found"}, status=404
            )

        scholar_dir = project_root / "scitex" / "scholar"
        if scholar_dir.exists():
            return JsonResponse(
                {"success": True, "message": "Scholar workspace already initialized"}
            )

        from scitex.scholar import ensure_workspace

        ensure_workspace(str(project_root))
        logger.info(f"Initialized scholar workspace for: {project.slug}")

        return JsonResponse(
            {"success": True, "message": "Scholar workspace initialized"}
        )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"Failed to initialize scholar workspace: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
