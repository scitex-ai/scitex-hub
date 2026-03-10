"""On-site page capture API for agent-workspace interaction."""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from pathlib import Path

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.workspace.console_app.models import CaptureRequest
from apps.infra.project_app.models import Project

logger = logging.getLogger(__name__)
USER_DATA_ROOT = Path("/app/data/users")


@login_required
@require_POST
def api_capture_request(request):
    """Create a capture request and notify browser via WebSocket.

    POST /console/api/on-site/capture/
    Body: {project_id: int, message?: str}
    Returns: {request_id: str}
    """
    body = json.loads(request.body) if request.body else {}
    project_id = body.get("project_id") or request.POST.get("project_id")
    message = body.get("message", "")

    if not project_id:
        return JsonResponse({"error": "project_id required"}, status=400)

    try:
        # Accept both numeric ID and slug string
        if str(project_id).isdigit():
            project = Project.objects.get(id=int(project_id))
        else:
            project = Project.objects.get(slug=project_id, owner=request.user)
    except Project.DoesNotExist:
        return JsonResponse({"error": "Project not found"}, status=404)

    # Check access
    if (
        project.owner != request.user
        and not project.collaborators.filter(id=request.user.id).exists()
    ):
        return JsonResponse({"error": "Access denied"}, status=403)

    # Check permission
    perm = _get_capture_permission(request.user, project)
    if perm == "deny":
        return JsonResponse(
            {"error": "Capture denied by user", "permission": "denied"}, status=403
        )

    # Create capture request
    capture_req = CaptureRequest.objects.create(
        project=project,
        user=request.user,
        description=message,
    )

    # Send capture request to browser via WebSocket
    channel_layer = get_channel_layer()
    group_name = f"capture_{request.user.username}"
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "capture.request",
            "request_id": str(capture_req.request_id),
            "project_id": project_id,
            "message": message,
            "needs_permission": perm == "ask",
        },
    )

    return JsonResponse(
        {
            "success": True,
            "request_id": str(capture_req.request_id),
        }
    )


@login_required
@require_GET
def api_capture_status(request, request_id):
    """Check capture request status.

    GET /console/api/on-site/capture/<request_id>/status/
    Returns: {status, filepath?, description?}
    """
    try:
        capture_req = CaptureRequest.objects.get(
            request_id=request_id,
            user=request.user,
        )
    except CaptureRequest.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    return JsonResponse(
        {
            "status": capture_req.status,
            "filepath": capture_req.filepath,
            "description": capture_req.description,
        }
    )


@login_required
@require_POST
def api_capture_upload(request):
    """Receive screenshot data from browser.

    POST /console/api/on-site/capture/upload/
    Body: {request_id: str, data: str (base64), format: str}
    """
    body = json.loads(request.body)
    request_id = body.get("request_id")
    image_data = body.get("data")  # base64 encoded
    img_format = body.get("format", "png")

    if not request_id or not image_data:
        return JsonResponse({"error": "request_id and data required"}, status=400)

    try:
        capture_req = CaptureRequest.objects.get(
            request_id=request_id,
            user=request.user,
            status="pending",
        )
    except CaptureRequest.DoesNotExist:
        return JsonResponse(
            {"error": "Request not found or already completed"}, status=404
        )

    # Save screenshot
    project = capture_req.project
    username = project.owner.username
    project_dir = USER_DATA_ROOT / username / "proj" / project.slug
    downloads_dir = project_dir / "scitex" / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_capture.{img_format}"
    filepath = downloads_dir / filename

    # Decode and save
    raw = base64.b64decode(image_data)
    filepath.write_bytes(raw)

    # Update request
    rel_path = f"scitex/downloads/{filename}"
    capture_req.status = "complete"
    capture_req.filepath = rel_path
    if not capture_req.description:
        capture_req.description = f"Page capture at {timestamp}"
    capture_req.save()

    logger.info("Capture saved: %s -> %s", request_id, filepath)
    return JsonResponse({"success": True, "filepath": rel_path})


@login_required
@require_POST
def api_capture_permission(request):
    """Set capture permission.

    POST /console/api/on-site/permission/
    Body: {scope: "project"|"global", action: "allow"|"deny", project_id?: int}
    """
    body = json.loads(request.body)
    scope = body.get("scope", "project")
    action = body.get("action", "allow")
    project_id = body.get("project_id")

    profile = request.user.profile
    prefs = profile.mcp_preferences or {}
    capture_prefs = prefs.get("on_site_capture", {})

    if scope == "global":
        capture_prefs["global"] = action == "allow"
    elif scope == "project" and project_id:
        projects = capture_prefs.get("projects", {})
        projects[str(project_id)] = action == "allow"
        capture_prefs["projects"] = projects

    prefs["on_site_capture"] = capture_prefs
    profile.mcp_preferences = prefs
    profile.save(update_fields=["mcp_preferences"])

    return JsonResponse({"success": True, "preferences": capture_prefs})


@login_required
@require_GET
def api_capture_permission_check(request):
    """Check current capture permission.

    GET /console/api/on-site/permission/?project_id=123
    """
    project_id = request.GET.get("project_id")
    perm = _get_capture_permission(request.user, project_id=project_id)
    return JsonResponse({"permission": perm})


def _get_capture_permission(user, project=None, project_id=None):
    """Check user's capture permission. Returns 'allow', 'deny', or 'ask'."""
    try:
        prefs = (user.profile.mcp_preferences or {}).get("on_site_capture", {})
    except Exception:
        return "ask"

    # Check global setting
    if "global" in prefs:
        return "allow" if prefs["global"] else "deny"

    # Check project-specific
    pid = str(project.id if project else project_id)
    if pid:
        projects = prefs.get("projects", {})
        if pid in projects:
            return "allow" if projects[pid] else "deny"

    return "ask"


# EOF
