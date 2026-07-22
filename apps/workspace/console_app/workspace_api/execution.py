"""
Code Workspace API Views - File operations for the simple editor.
"""

import json
import logging
import subprocess
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.models import Project

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def api_execute_script(request):
    """Execute a Python script via setpriv (UID isolation).

    Security model mirrors :func:`api_execute_command`:
    - Requires login — no unauthenticated access (``@login_required``)
    - Caller must own or collaborate on the project
    - Script runs under the user's OS UID/GID via setpriv (argv list, no shell)
    - Project directory validated to be within the user's data jail
    - Minimal environment (NO Django secrets exposed)
    """
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")
        file_path = data.get("path")
        args = data.get("args", [])

        if not project_id or not file_path:
            return JsonResponse({"error": "Missing required fields"}, status=400)

        # ``args`` is spliced into argv — a bare string would be iterated
        # character-by-character into separate arguments. Reject it loudly.
        if not isinstance(args, list):
            return JsonResponse({"error": "'args' must be a list"}, status=400)

        project = Project.objects.select_related("owner").get(id=project_id)

        # Permission: must be owner or collaborator.
        # NOTE: the jail check below additionally requires the project directory
        # to live under the REQUESTING user's data root, so today only the owner
        # can actually reach execution. Same shape as api_execute_command.
        has_access = (
            request.user == project.owner
            or request.user in project.collaborators.all()
        )
        if not has_access:
            return JsonResponse({"error": "Unauthorized"}, status=403)

        from apps.infra.accounts_app.services.unix_user import (
            ensure_linux_account,
            get_unix_uid,
        )
        from apps.infra.project_app.services.filesystem.permissions import (
            get_user_data_root,
            validate_path_in_project,
            validate_path_in_user_jail,
        )

        # Resolve and validate the project dir — must be within the user's jail
        project_dir = Path(project.git_clone_path)
        jail = get_user_data_root(request.user)
        if not validate_path_in_user_jail(request.user, project_dir):
            logger.warning(
                "api_execute_script: project dir %s outside jail for %s",
                project_dir,
                request.user.username,
            )
            return JsonResponse(
                {"error": "Access denied: project directory outside your home."},
                status=403,
            )

        file_full_path = project_dir / file_path

        # Path-traversal check — resolved file must stay within the project dir.
        # Component-wise containment, NOT a string prefix: `startswith` would
        # accept a sibling directory that merely shares the prefix (project
        # "/data/u/proj" would admit "/data/u/proj-other/x.py").
        if not validate_path_in_project(project_dir, file_full_path):
            return JsonResponse({"error": "Invalid file path"}, status=400)

        # Defence in depth — resolved file must also stay within the user's jail
        if not validate_path_in_user_jail(request.user, file_full_path):
            return JsonResponse({"error": "Invalid file path"}, status=400)

        if file_full_path.suffix != ".py":
            return JsonResponse(
                {"error": "Only Python files can be executed"}, status=400
            )

        if not file_full_path.exists():
            return JsonResponse({"error": "File not found"}, status=404)

        # Ensure Linux account exists (idempotent). A failure here does NOT
        # weaken the privilege drop — setpriv takes a numeric UID and works
        # without a passwd entry — but it must never pass silently.
        try:
            ensure_linux_account(request.user)
        except Exception as exc:
            logger.error(
                "api_execute_script: ensure_linux_account failed for %s: %s",
                request.user.username,
                exc,
                exc_info=True,
            )

        uid = get_unix_uid(request.user)
        username = request.user.username

        env = {
            "HOME": str(jail),
            "USER": username,
            "LOGNAME": username,
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "TERM": "xterm-256color",
            "SCITEX_HUB_CODE_WORKSPACE": "true",
            "SCITEX_HUB_CODE_BACKEND": "inline",
            "SCITEX_HUB_CODE_SESSION_ID": str(project.id),
            "SCITEX_HUB_CODE_PROJECT_ROOT": str(project_dir),
        }

        try:
            result = subprocess.run(
                [
                    "setpriv",
                    f"--reuid={uid}",
                    f"--regid={uid}",
                    "--clear-groups",
                    "--",
                    "python",
                    str(file_full_path),
                    *[str(a) for a in args],
                ],
                cwd=str(file_full_path.parent),
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
            )
        except FileNotFoundError as exc:
            logger.error("api_execute_script: cannot spawn setpriv: %s", exc)
            return JsonResponse(
                {"error": "setpriv not found. Ensure util-linux is installed."},
                status=500,
            )

        return JsonResponse(
            {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "path": file_path,
            }
        )

    except subprocess.TimeoutExpired:
        return JsonResponse(
            {"error": "Script execution timed out (5 min limit)"}, status=408
        )
    except Exception as e:
        logger.error(f"Error executing script: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_execute_command(request):
    """Execute a bash command in user's project directory via setpriv (UID isolation).

    Security model:
    - Requires login — no unauthenticated access
    - Caller must own or collaborate on the project
    - Command runs under the user's OS UID/GID via setpriv (no shell=True)
    - Project directory validated to be within user's data jail
    - Minimal environment (no Django secrets exposed)
    """
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")
        command = data.get("command", "").strip()

        if not project_id or not command:
            return JsonResponse({"error": "Missing required fields"}, status=400)

        project = Project.objects.select_related("owner").get(id=project_id)

        # Permission: must be owner or collaborator
        has_access = (
            request.user == project.owner or request.user in project.collaborators.all()
        )
        if not has_access:
            return JsonResponse({"error": "Unauthorized"}, status=403)

        from apps.infra.accounts_app.services.unix_user import (
            ensure_linux_account,
            get_unix_uid,
        )
        from apps.infra.project_app.services.filesystem.permissions import (
            get_user_data_root,
            validate_path_in_user_jail,
        )

        # Resolve and validate CWD — must be within the requesting user's jail
        project_dir = Path(project.git_clone_path)
        jail = get_user_data_root(request.user)
        if not validate_path_in_user_jail(request.user, project_dir):
            logger.warning(
                "api_execute_command: CWD %s outside jail for %s",
                project_dir,
                request.user.username,
            )
            return JsonResponse(
                {"error": "Access denied: project directory outside your home."},
                status=403,
            )

        # Ensure Linux account exists (idempotent, best-effort)
        try:
            ensure_linux_account(request.user)
        except Exception:
            pass

        uid = get_unix_uid(request.user)
        username = request.user.username

        env = {
            "HOME": str(jail),
            "USER": username,
            "LOGNAME": username,
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "TERM": "xterm-256color",
            "SCITEX_HUB_CODE_WORKSPACE": "true",
            "SCITEX_HUB_CODE_BACKEND": "inline",
            "SCITEX_HUB_CODE_SESSION_ID": str(project.id),
            "SCITEX_HUB_CODE_PROJECT_ROOT": str(project_dir),
        }

        result = subprocess.run(
            [
                "setpriv",
                f"--reuid={uid}",
                f"--regid={uid}",
                "--clear-groups",
                "--",
                "bash",
                "-c",
                command,
            ],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        return JsonResponse(
            {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "cwd": str(project_dir),
            }
        )

    except subprocess.TimeoutExpired:
        return JsonResponse({"error": "Command timed out (30 sec limit)"}, status=408)
    except FileNotFoundError:
        return JsonResponse(
            {"error": "setpriv not found. Ensure util-linux is installed."}, status=500
        )
    except Exception as e:
        logger.error("Error executing command: %s", e, exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


# EOF
