"""
Code Workspace API Views - File operations for the simple editor.
"""

import json
import logging
import subprocess
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from apps.project_app.models import Project
from apps.project_app.services.git_status import get_git_status, get_file_diff
from apps.project_app.services.git_service import git_commit_and_push

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def api_execute_script(request):
    """Execute a Python script."""
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")
        file_path = data.get("path")
        args = data.get("args", [])

        if not project_id or not file_path:
            return JsonResponse({"error": "Missing required fields"}, status=400)

        project = Project.objects.select_related("owner").get(id=project_id)

        # Check permissions (allow authenticated users and visitors with allocated project)
        if request.user.is_authenticated:
            has_access = (
                request.user == project.owner
                or request.user in project.collaborators.all()
            )
        else:
            # For visitor users, check if this is their allocated visitor project
            visitor_project_id = request.session.get("visitor_project_id")
            has_access = (visitor_project_id and project.id == visitor_project_id)

        if not has_access:
            return JsonResponse({"error": "Unauthorized"}, status=403)

        file_full_path = Path(project.git_clone_path) / file_path

        # Security checks
        if not str(file_full_path.resolve()).startswith(
            str(Path(project.git_clone_path).resolve())
        ):
            return JsonResponse({"error": "Invalid file path"}, status=400)

        if not file_full_path.exists():
            return JsonResponse({"error": "File not found"}, status=404)

        if file_full_path.suffix != ".py":
            return JsonResponse(
                {"error": "Only Python files can be executed"}, status=400
            )

        result = subprocess.run(
            ["python", str(file_full_path)] + args,
            cwd=file_full_path.parent,
            capture_output=True,
            text=True,
            timeout=300,
        )

        return JsonResponse({
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "path": file_path,
        })

    except subprocess.TimeoutExpired:
        return JsonResponse(
            {"error": "Script execution timed out (5 min limit)"}, status=408
        )
    except Exception as e:
        logger.error(f"Error executing script: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_execute_command(request):
    """Execute a bash command in user's home directory context."""
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")
        command = data.get("command", "").strip()

        if not project_id or not command:
            return JsonResponse({"error": "Missing required fields"}, status=400)

        project = Project.objects.select_related("owner").get(id=project_id)

        # Check permissions (allow authenticated users and visitors with allocated project)
        if request.user.is_authenticated:
            has_access = (
                request.user == project.owner
                or request.user in project.collaborators.all()
            )
        else:
            # For visitor users, check if this is their allocated visitor project
            visitor_project_id = request.session.get("visitor_project_id")
            has_access = (visitor_project_id and project.id == visitor_project_id)

        if not has_access:
            return JsonResponse({"error": "Unauthorized"}, status=403)

        # Security: Block dangerous commands
        dangerous_commands = ['rm -rf /', 'dd', 'mkfs', ':(){:|:&};:', 'chmod -R 777 /']
        if any(dangerous in command for dangerous in dangerous_commands):
            return JsonResponse(
                {"error": "Dangerous command blocked"}, status=403
            )

        # Get user info and project directory
        import os
        username = project.owner.username
        # Use /home/username as home dir (standard Linux path)
        home_dir = f"/home/{username}"
        project_dir = Path(project.git_clone_path)

        # Set up environment to feel like user's terminal
        env = os.environ.copy()
        env['HOME'] = home_dir
        env['USER'] = username
        env['LOGNAME'] = username
        env['PWD'] = str(project_dir)
        env['HOSTNAME'] = 'scitex-cloud'
        env['TERM'] = 'xterm-256color'  # Enable terminal features like clear

        # SciTeX Cloud Code-specific env vars for scitex.plt auto-detection
        env['SCITEX_CLOUD_CODE_WORKSPACE'] = 'true'  # Marker for scitex.plt
        env['SCITEX_CLOUD_CODE_BACKEND'] = 'inline'  # Use inline plotting in terminal
        env['SCITEX_CLOUD_CODE_SESSION_ID'] = str(project.id)  # Session tracking
        env['SCITEX_CLOUD_CODE_PROJECT_ROOT'] = str(project_dir)  # Project root
        env['SCITEX_CLOUD_CODE_USERNAME'] = username  # Username for debugging

        # Remove other sensitive Django env vars from user's view
        sensitive_vars = [k for k in env.keys() if (k.startswith('DJANGO_') or 'SECRET' in k or 'PASSWORD' in k or 'API_KEY' in k) and not k.startswith('SCITEX_')]
        for var in sensitive_vars:
            env.pop(var, None)

        # Execute command in project directory (like cd ~/proj/project-name)
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        return JsonResponse({
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": str(project_dir),
        })

    except subprocess.TimeoutExpired:
        return JsonResponse(
            {"error": "Command timed out (30 sec limit)"}, status=408
        )
    except Exception as e:
        logger.error(f"Error executing command: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


# EOF
