"""Bash execution endpoint for the AI chat "!" prefix mode."""

import asyncio
import json
from pathlib import Path

from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.accounts_app.services.unix_user import (
    enforce_data_dir_ownership,
    ensure_linux_account,
    get_unix_uid,
)
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


def _ensure_user_provisioned(user) -> None:
    """Best-effort: create Linux account + fix data dir ownership if missing."""
    try:
        ensure_linux_account(user)
        enforce_data_dir_ownership(user)
    except Exception:
        pass  # Non-fatal; setpriv will fail if account is missing (handled below)


@transaction.non_atomic_requests
@login_required
@require_http_methods(["POST"])
async def api_bash_exec(request):
    """Execute a shell command as the requesting user's Linux UID via setpriv.

    Security model:
    - CWD is validated to be within user's data jail (validate_path_in_user_jail)
    - Command runs under the user's OS UID/GID (setpriv --reuid/--regid)
    - Data directory is chmod 700 — other UIDs cannot read it
    - Minimal environment (HOME, USER, PATH only)

    Used by the AI chat "!" prefix mode (e.g. "! ls").
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

    # Hard permission check: CWD must be within user's jail
    if not await sync_to_async(validate_path_in_user_jail)(request.user, cwd_path):
        return JsonResponse(
            {"error": "Access denied: working directory outside your home."},
            status=403,
        )

    # Ensure Linux account exists (idempotent)
    await sync_to_async(_ensure_user_provisioned)(request.user)

    jail = await sync_to_async(get_user_data_root)(request.user)
    uid = await sync_to_async(get_unix_uid)(request.user)
    gid = uid

    jail_str = str(jail)
    cwd_str = str(cwd_path)
    username = str(request.user.username)

    # Minimal environment — strip inherited vars that could leak info or be abused
    env = {
        "HOME": jail_str,
        "USER": username,
        "LOGNAME": username,
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "TERM": "xterm-256color",
    }

    try:
        proc = await asyncio.create_subprocess_exec(
            "setpriv",
            f"--reuid={uid}",
            f"--regid={gid}",
            "--clear-groups",
            "--",
            "bash",
            "-c",
            command,
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

    except FileNotFoundError:
        return JsonResponse(
            {
                "error": "setpriv not found. Ensure util-linux is installed in the container."
            },
            status=500,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
