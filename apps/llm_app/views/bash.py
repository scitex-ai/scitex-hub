"""Bash execution endpoint for the AI chat "!" prefix mode."""

import asyncio
import json
from pathlib import Path

from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.project_app.services.filesystem.permissions import (
    get_user_data_root,
    validate_path_in_user_jail,
)

_TIMEOUT_SECONDS = 30


def _get_project_cwd(user, project_slug: str) -> Path:
    """Resolve CWD for the bash command (sync DB lookup). Always within user's jail."""
    jail = get_user_data_root(user)

    if not project_slug:
        return jail

    try:
        from apps.project_app.models import Project
        from apps.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        project = Project.objects.get(owner=user, slug=project_slug)
        manager = get_project_filesystem_manager(user)
        path = manager.get_project_root_path(project)
        if path and path.exists() and validate_path_in_user_jail(user, path):
            return path
    except Exception:
        pass

    return jail


def _build_jailed_command(command: str, jail: str) -> str:
    """
    Wrap the user command so that `cd` cannot navigate outside the jail.

    Note: this prevents directory-traversal via `cd` but does NOT prevent
    reading files via absolute paths — OS-level sandboxing (chroot/namespaces)
    is required for complete isolation.
    """
    safe_jail = jail.replace("'", "'\\''")
    return f"""_JAIL='{safe_jail}'
cd() {{
    if [ $# -eq 0 ]; then
        builtin cd "$_JAIL" || return 1
    else
        builtin cd "$@" || return 1
    fi
    _cur="$(pwd -P 2>/dev/null)"
    case "$_cur" in
        "$_JAIL"|"$_JAIL"/*) ;;
        *)
            builtin cd - >/dev/null 2>&1
            echo "Access denied: cannot navigate outside your home directory" >&2
            return 1
            ;;
    esac
}}
{command}
"""


@transaction.non_atomic_requests
@login_required
@require_http_methods(["POST"])
async def api_bash_exec(request):
    """Execute a shell command restricted to the requesting user's data directory.

    Used by the AI chat "!" prefix mode (e.g. "! ls").
    CWD is jailed to /data/users/<username>/ via validate_path_in_user_jail.
    The `cd` built-in is wrapped to prevent navigating outside the jail.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    command = data.get("command", "").strip()
    if not command:
        return JsonResponse({"error": "command is required"}, status=400)

    project_slug = data.get("project_slug", "").strip()
    cwd_path = await sync_to_async(_get_project_cwd)(request.user, project_slug)

    # Hard permission check using centralised validator
    jail = await sync_to_async(get_user_data_root)(request.user)
    if not await sync_to_async(validate_path_in_user_jail)(request.user, cwd_path):
        return JsonResponse(
            {"error": "Access denied: working directory outside your home."},
            status=403,
        )

    jail_str = str(jail)
    cwd_str = str(cwd_path)
    wrapped = _build_jailed_command(command, jail_str)

    # Minimal environment — strip inherited vars that could leak info or be abused
    env = {
        "HOME": jail_str,
        "USER": str(request.user.username),
        "LOGNAME": str(request.user.username),
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "TERM": "xterm-256color",
    }

    try:
        proc = await asyncio.create_subprocess_shell(
            wrapped,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd_str,
            env=env,
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
                "cwd": cwd_str,
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
