"""Bash execution endpoint for the AI chat "!" prefix mode."""

import asyncio
import json

from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

_TIMEOUT_SECONDS = 30
_FALLBACK_CWD = "/app"


def _get_project_cwd(user, project_slug: str) -> str:
    """Resolve CWD for the bash command from project slug (sync DB lookup)."""
    if not project_slug:
        return _FALLBACK_CWD
    try:
        from apps.project_app.models import Project
        from apps.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        project = Project.objects.get(owner=user, slug=project_slug)
        manager = get_project_filesystem_manager(user)
        path = manager.get_project_root_path(project)
        if path and path.exists():
            return str(path)
    except Exception:
        pass
    return _FALLBACK_CWD


@transaction.non_atomic_requests
@login_required
@require_http_methods(["POST"])
async def api_bash_exec(request):
    """Execute a shell command in the user's active project directory.

    Used by the AI chat "!" prefix mode (e.g. "! ls").
    CWD is the project root resolved from project_slug + request.user.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    command = data.get("command", "").strip()
    if not command:
        return JsonResponse({"error": "command is required"}, status=400)

    project_slug = data.get("project_slug", "").strip()
    cwd = await sync_to_async(_get_project_cwd)(request.user, project_slug)

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            proc.kill()
            return JsonResponse(
                {"error": f"Command timed out after {_TIMEOUT_SECONDS}s"},
                status=408,
            )

        return JsonResponse(
            {
                "stdout": stdout_bytes.decode("utf-8", errors="replace"),
                "stderr": stderr_bytes.decode("utf-8", errors="replace"),
                "returncode": proc.returncode,
                "cwd": cwd,
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
