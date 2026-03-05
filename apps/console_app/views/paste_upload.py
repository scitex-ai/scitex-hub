"""Paste upload endpoint for terminal clipboard and drag-drop."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.project_app.models import Project

logger = logging.getLogger(__name__)

USER_DATA_ROOT = Path("/app/data/users")


@login_required
@require_POST
def api_paste_upload(request):
    """Upload pasted/dropped files to project's scitex/downloads/ directory.

    POST /console/api/paste-upload/
    Body: multipart form with 'files' field and 'project_id' field
    Returns: {"paths": ["scitex/downloads/20260305_014523_screenshot.png"]}
    """
    project_id = request.POST.get("project_id")
    if not project_id:
        return JsonResponse({"error": "project_id required"}, status=400)

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({"error": "Project not found"}, status=404)

    # Check access
    if (
        project.owner != request.user
        and not project.collaborators.filter(id=request.user.id).exists()
    ):
        return JsonResponse({"error": "Access denied"}, status=403)

    files = request.FILES.getlist("files")
    if not files:
        return JsonResponse({"error": "No files provided"}, status=400)

    username = project.owner.username
    project_dir = USER_DATA_ROOT / username / "proj" / project.slug
    downloads_dir = project_dir / "scitex" / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_paths = []

    for f in files:
        # Sanitize filename
        safe_name = f.name.replace("/", "_").replace("\\", "_").replace("..", "_")
        filename = f"{timestamp}_{safe_name}"
        filepath = downloads_dir / filename

        with open(filepath, "wb") as dest:
            for chunk in f.chunks():
                dest.write(chunk)

        # Return path relative to project root
        saved_paths.append(f"scitex/downloads/{filename}")
        logger.info("Paste upload: %s -> %s", f.name, filepath)

    return JsonResponse({"paths": saved_paths})
