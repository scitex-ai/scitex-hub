# -*- coding: utf-8 -*-
# Timestamp: 2025-11-25 23:20:00
# Author: ywatanabe
# File: apps/console_app/job_api_views.py

"""
SLURM job management API views for SciTeX Hub.

Provides REST API endpoints for submitting and managing computational jobs
through SLURM and Apptainer containers.
"""

import json
import logging
import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .services import SlurmManager
from .services.job_ownership import job_belongs_to_user

logger = logging.getLogger(__name__)

# Lazy-load SLURM manager to avoid initialization errors
_slurm_manager = None


def get_slurm_manager():
    """Get or create SLURM manager instance."""
    global _slurm_manager
    if _slurm_manager is None:
        _slurm_manager = SlurmManager()
    return _slurm_manager


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_submit_job(request):
    """
    Submit a computational job to SLURM.

    POST /code/api/jobs/submit/
    Body: {
        "script_path": "/workspace/analysis.py",
        "job_name": "my_analysis",
        "cpus": 2,
        "memory_gb": 4,
        "time_limit": "01:00:00",
        "partition": "normal",
        "env_vars": {"DEBUG": "1"}
    }

    Returns:
        {
            "success": true,
            "job_id": 42,
            "partition": "normal",
            "message": "Job 42 submitted successfully"
        }
    """
    try:
        data = json.loads(request.body)

        # Get user workspace
        user_workspace = get_user_workspace(request.user)

        # Get container path from terminal config (respects env vars)
        from apps.workspace.console_app.views.terminal.config import (
            SLURM_CONTAINER_PATH,
        )

        container_path = Path(SLURM_CONTAINER_PATH)

        # SECURITY: the SLURM job NAME is the only ownership signal we have
        # (no DB record maps job_id -> user). The status/cancel/output
        # endpoints authorize via job_belongs_to_user, which keys on the
        # "scitex_<username>_" prefix. So every submitted job MUST carry that
        # prefix -- otherwise the owner is locked out of their OWN job and
        # api_user_jobs will not list it. The user-supplied label is
        # sanitized to a safe charset and length-capped before use.
        raw_label = data.get("job_name", "job")
        safe_label = re.sub(r"[^A-Za-z0-9._-]", "_", str(raw_label))[:64] or "job"
        job_name = f"scitex_{request.user.username}_{safe_label}"

        # Submit job
        result = get_slurm_manager().submit_job(
            user_id=str(request.user.id),
            script_path=Path(data.get("script_path")),
            container_path=container_path,
            workspace=user_workspace,
            job_name=job_name,
            partition=data.get("partition", "normal"),
            cpus=data.get("cpus", 1),
            memory_gb=data.get("memory_gb", 4),
            time_limit=data.get("time_limit", "01:00:00"),
            env_vars=data.get("env_vars", {}),
        )

        if result["success"]:
            logger.info(
                f"Job {result['job_id']} submitted for user {request.user.username}"
            )
        else:
            logger.error(
                f"Job submission failed for user {request.user.username}: {result['message']}"
            )

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON in request body"}, status=400
        )
    except Exception as e:
        logger.error(
            f"Job submission error for user {request.user.username}: {str(e)}",
            exc_info=True,
        )
        return JsonResponse(
            {"success": False, "message": f"Server error: {str(e)}"}, status=500
        )


@login_required
@require_http_methods(["GET"])
def api_job_status(request, job_id):
    """
    Get status of a SLURM job.

    GET /code/api/jobs/{job_id}/status/

    Returns:
        {
            "job_id": 42,
            "state": "RUNNING",
            "time_used": "0:05:23",
            "is_running": true,
            "is_pending": false,
            "is_completed": false
        }
    """
    try:
        job_id = int(job_id)
        # SECURITY (IDOR): only the owner may read a job's state. 404 (not
        # 403) so a job owned by someone else is indistinguishable from a
        # nonexistent one -- no existence disclosure.
        if not job_belongs_to_user(
            get_slurm_manager(), job_id, request.user.username
        ):
            return JsonResponse(
                {"success": False, "message": "Not found"}, status=404
            )
        status = get_slurm_manager().get_job_status(job_id)
        return JsonResponse(status)
    except Exception as e:
        logger.error(f"Error getting job {job_id} status: {str(e)}", exc_info=True)
        return JsonResponse(
            {"success": False, "message": f"Error: {str(e)}"}, status=500
        )


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_cancel_job(request, job_id):
    """
    Cancel a running SLURM job.

    POST /code/api/jobs/{job_id}/cancel/

    Returns:
        {
            "success": true,
            "message": "Job 42 cancelled"
        }
    """
    try:
        job_id = int(job_id)
        # SECURITY (IDOR): without this check any authenticated user could
        # cancel ANY user's job by numeric id. 404 (not 403) so a job owned
        # by someone else is indistinguishable from a nonexistent one.
        if not job_belongs_to_user(
            get_slurm_manager(), job_id, request.user.username
        ):
            return JsonResponse(
                {"success": False, "message": "Not found"}, status=404
            )
        result = get_slurm_manager().cancel_job(job_id)
        if result["success"]:
            logger.info(f"Job {job_id} cancelled by user {request.user.username}")
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {str(e)}", exc_info=True)
        return JsonResponse(
            {"success": False, "message": f"Error: {str(e)}"}, status=500
        )


@login_required
@require_http_methods(["GET"])
def api_job_output(request, job_id):
    """
    Get output logs for a job.

    GET /code/api/jobs/{job_id}/output/?tail=100

    Returns:
        {
            "found": true,
            "stdout": "...",
            "stderr": "..."
        }
    """
    try:
        job_id = int(job_id)
        # SECURITY (IDOR): defense-in-depth. This endpoint is already
        # workspace-scoped (it only reads .../user_{id}/slurm_outputs/), so
        # it is not an active cross-tenant leak, but the ownership gate is
        # applied here too for consistency. 404 (not 403): no existence
        # disclosure.
        if not job_belongs_to_user(
            get_slurm_manager(), job_id, request.user.username
        ):
            return JsonResponse(
                {"success": False, "message": "Not found"}, status=404
            )
        tail_lines = int(request.GET.get("tail", 100))
        user_workspace = get_user_workspace(request.user)

        output = get_slurm_manager().get_job_output(
            job_id=job_id, workspace=user_workspace, tail_lines=tail_lines
        )

        return JsonResponse(output)
    except Exception as e:
        logger.error(f"Error getting job {job_id} output: {str(e)}", exc_info=True)
        return JsonResponse({"found": False, "message": f"Error: {str(e)}"}, status=500)


@login_required
@require_http_methods(["GET"])
def api_queue_status(request):
    """
    Get overall cluster/queue status.

    GET /code/api/jobs/queue/

    Returns:
        {
            "running": 5,
            "pending": 2,
            "total": 7,
            "cpu_allocation": "8/16/0/24"
        }
    """
    try:
        status = get_slurm_manager().get_queue_status()
        return JsonResponse(status)
    except Exception as e:
        logger.error(f"Error getting queue status: {str(e)}", exc_info=True)
        return JsonResponse(
            {"success": False, "message": f"Error: {str(e)}"}, status=500
        )


@login_required
@require_http_methods(["GET"])
def api_user_jobs(request):
    """
    Get list of jobs for current user.

    GET /code/api/jobs/?state=running

    Query params:
        - state: Filter by state (running/pending/all)
        - user: Filter by user (default: all users visible)

    Returns:
        {
            "success": true,
            "jobs": [
                {"job_id": 42, "state": "RUNNING", ...},
                {"job_id": 41, "state": "PENDING", ...}
            ],
            "running": 1,
            "pending": 1,
            "total": 2,
            "slurm_available": true
        }
    """
    try:
        slurm = get_slurm_manager()

        # Check if SLURM is available
        if not slurm.is_available():
            return JsonResponse(
                {
                    "success": True,
                    "jobs": [],
                    "running": 0,
                    "pending": 0,
                    "total": 0,
                    "slurm_available": False,
                    "message": "SLURM is not available on this system",
                }
            )

        # Get filter parameters
        state_filter = request.GET.get("state", "all")

        # Get all jobs from SLURM, then filter by current user's job name
        # Jobs run as root in Docker, so we filter by job name prefix
        result = slurm.list_jobs(state=state_filter)

        # Filter to only show jobs belonging to the current user
        # Matches both compute jobs (scitex_{user}_*) and terminal
        # allocations (scitex-hub-terminal-{user})
        username = request.user.username
        compute_prefix = f"scitex_{username}_"
        terminal_prefix = f"scitex-hub-terminal-{username}"

        def _is_user_job(job):
            name = job.get("name", "")
            return name.startswith(compute_prefix) or name.startswith(terminal_prefix)

        user_jobs = [j for j in result.get("jobs", []) if _is_user_job(j)]

        # Add type field for UI differentiation
        for job in user_jobs:
            name = job.get("name", "")
            job["type"] = (
                "terminal" if name.startswith("scitex-hub-terminal") else "compute"
            )

        running = sum(1 for j in user_jobs if j["state"] == "RUNNING")
        pending = sum(1 for j in user_jobs if j["state"] == "PENDING")
        result["jobs"] = user_jobs
        result["running"] = running
        result["pending"] = pending
        result["total"] = len(user_jobs)
        result["slurm_available"] = True

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Error getting user jobs: {str(e)}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "jobs": [],
                "running": 0,
                "pending": 0,
                "total": 0,
                "slurm_available": False,
                "message": f"Error: {str(e)}",
            },
            status=500,
        )


def get_user_workspace(user):
    """
    Get workspace path for user.

    Args:
        user: Django User object

    Returns:
        Path: User workspace directory
    """
    # Check if user has a workspace in settings
    base_workspace = Path(
        getattr(settings, "USER_WORKSPACE_BASE", "/tmp/scitex_workspaces")
    )

    user_workspace = base_workspace / f"user_{user.id}"
    user_workspace.mkdir(parents=True, exist_ok=True)

    return user_workspace


# EOF
