# -*- coding: utf-8 -*-
# Timestamp: 2026-03-04
# Author: ywatanabe
# File: apps/platform_app/views/api/jobqueue.py

"""
REST API views for JobQueue.

Endpoints
---------
POST   /api/platform/jobs/<app>/submit/          — submit a job
GET    /api/platform/jobs/<app>/<job_id>/        — status + result
POST   /api/platform/jobs/<app>/<job_id>/cancel/ — cancel a job
GET    /api/platform/jobs/<app>/                 — list user's jobs
"""

import json
import logging  # noqa: STX-I007 — Django context, no @stx.session

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger("scitex")


def _parse_body(request) -> dict:
    """Parse JSON request body, return empty dict on failure."""
    try:
        return json.loads(request.body) if request.body else {}
    except (json.JSONDecodeError, ValueError):
        return {}


def _resolve_project(project_id, owner):
    """Return Project instance or None."""
    if not project_id:
        return None
    try:
        from apps.infra.project_app.models import Project

        return Project.objects.get(pk=project_id, members=owner)
    except Exception:
        return None


@login_required
@require_http_methods(["POST"])
def job_submit(request, app: str) -> JsonResponse:
    """
    Submit a new background job.

    Request body (JSON)
    -------------------
    job_name   : str  — name of the job handler to invoke
    project_id : str  — UUID of the project (optional)
    params     : dict — arbitrary params forwarded to the job handler
    """
    from apps.infra.platform_app.services.jobqueue import jobqueue

    body = _parse_body(request)
    job_name = body.get("job_name", "")
    if not job_name:
        return JsonResponse({"error": "job_name is required"}, status=400)

    project = _resolve_project(body.get("project_id"), request.user)
    params = body.get("params") or {}

    try:
        job = jobqueue.submit(
            app_name=app,
            job_name=job_name,
            project=project,
            owner=request.user,
            params=params,
        )
    except Exception as exc:
        logger.exception("job_submit failed for app=%s job=%s", app, job_name)
        return JsonResponse({"error": str(exc)}, status=500)

    return JsonResponse(
        {"job_id": str(job.id), "status": job.status},
        status=201,
    )


@login_required
@require_http_methods(["GET"])
def job_detail(request, app: str, job_id) -> JsonResponse:
    """Return status and result for a specific job."""
    from apps.infra.platform_app.models import PlatformJob
    from apps.infra.platform_app.services.jobqueue import jobqueue

    try:
        job = PlatformJob.objects.get(pk=job_id, owner=request.user, app_name=app)
    except PlatformJob.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)

    info = jobqueue.status(str(job.id))
    if info is None:
        return JsonResponse({"error": "Job not found"}, status=404)

    if job.status == PlatformJob.Status.COMPLETED:
        info["result"] = jobqueue.result(str(job.id))

    return JsonResponse(info)


@login_required
@require_http_methods(["POST"])
def job_cancel(request, app: str, job_id) -> JsonResponse:
    """Cancel a queued or running job."""
    from apps.infra.platform_app.models import PlatformJob
    from apps.infra.platform_app.services.jobqueue import jobqueue

    try:
        PlatformJob.objects.get(pk=job_id, owner=request.user, app_name=app)
    except PlatformJob.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)

    cancelled = jobqueue.cancel(str(job_id))
    if not cancelled:
        return JsonResponse(
            {"error": "Job cannot be cancelled in its current state"},
            status=409,
        )

    return JsonResponse({"job_id": str(job_id), "cancelled": True})


@login_required
@require_http_methods(["GET"])
def job_list(request, app: str) -> JsonResponse:
    """List all jobs owned by the current user for a given app."""
    from apps.infra.platform_app.services.jobqueue import jobqueue

    project_id = request.GET.get("project_id")
    project = _resolve_project(project_id, request.user) if project_id else None

    qs = jobqueue.list_jobs(
        app_name=app,
        project=project,
        owner=request.user,
    )

    jobs = [
        {
            "id": str(j.id),
            "job_name": j.job_name,
            "status": j.status,
            "progress_percent": j.progress_percent,
            "progress_message": j.progress_message,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "finished_at": j.finished_at.isoformat() if j.finished_at else None,
        }
        for j in qs
    ]

    return JsonResponse({"jobs": jobs, "count": len(jobs)})


# EOF
