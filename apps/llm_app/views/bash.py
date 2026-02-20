"""Bash execution endpoint for the AI chat "!" prefix mode."""

import asyncio
import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

# Project root is the working directory for user commands
_PROJECT_ROOT = "/home/ywatanabe/proj/scitex-cloud"
_TIMEOUT_SECONDS = 30


@transaction.non_atomic_requests
@login_required
@require_http_methods(["POST"])
async def api_bash_exec(request):
    """Execute a shell command and return stdout/stderr.

    Used by the AI chat "!" prefix mode (e.g. "! ls").
    Runs inside the Docker container with project root as CWD.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    command = data.get("command", "").strip()
    if not command:
        return JsonResponse({"error": "command is required"}, status=400)

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=_PROJECT_ROOT,
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
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
