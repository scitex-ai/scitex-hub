# -*- coding: utf-8 -*-
# Timestamp: 2026-03-04
# Author: ywatanabe
# File: apps/platform_app/services/jobqueue/executor.py

"""
JobQueue executor: submit, status, cancel, result, list_jobs.

Celery task wrapper updates job status on start/success/failure
and stores result or error in the PlatformJob record.
"""

import logging  # noqa: STX-I007 — Django context, no @stx.session
from typing import Any, Dict, Optional

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

logger = logging.getLogger("scitex")


# ---------------------------------------------------------------------------
# Celery task wrapper
# ---------------------------------------------------------------------------


@shared_task(
    bind=True,
    name="apps.infra.platform_app.services.jobqueue.executor.run_platform_job",
    max_retries=0,
    soft_time_limit=3600,
    time_limit=3660,
)
def run_platform_job(self, job_id: str) -> Dict:
    """
    Generic Celery task wrapper for PlatformJob execution.

    Imports the actual callable registered under (app_name, job_name),
    updates job status fields, and persists result/error.
    """
    from django.utils import timezone

    from apps.infra.platform_app.models import PlatformJob

    try:
        job = PlatformJob.objects.get(pk=job_id)
    except PlatformJob.DoesNotExist:
        logger.error("PlatformJob %s not found", job_id)
        return {"success": False, "error": "Job record not found"}

    # Mark running
    job.status = PlatformJob.Status.RUNNING
    job.started_at = timezone.now()
    job.celery_task_id = self.request.id or ""
    job.save(update_fields=["status", "started_at", "celery_task_id"])

    try:
        callable_fn = _resolve_callable(job.app_name, job.job_name)
        result = callable_fn(job_id=str(job.id), **job.params)

        job.status = PlatformJob.Status.COMPLETED
        job.result = result
        job.progress_percent = 100
        job.finished_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "result",
                "progress_percent",
                "finished_at",
            ]
        )
        return {"success": True, "job_id": str(job.id)}

    except SoftTimeLimitExceeded:
        msg = "Job timed out"
        logger.warning("PlatformJob %s timed out", job_id)
        _mark_failed(job, msg)
        return {"success": False, "error": msg}

    except Exception as exc:
        msg = str(exc)
        logger.exception("PlatformJob %s failed: %s", job_id, msg)
        _mark_failed(job, msg)
        return {"success": False, "error": msg}


def _mark_failed(job, error_message: str) -> None:
    from django.utils import timezone

    from apps.infra.platform_app.models import PlatformJob

    job.status = PlatformJob.Status.FAILED
    job.error_message = error_message
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "error_message", "finished_at"])


def _resolve_callable(app_name: str, job_name: str):
    """
    Resolve the Python callable for a given (app_name, job_name) pair.

    Convention: each app registers its jobs in
        apps.<app_name>.services.jobs.<job_name>.execute(job_id, **params)
    """
    import importlib

    module_path = f"apps.{app_name}.services.jobs.{job_name}"
    try:
        module = importlib.import_module(module_path)
        return module.execute
    except (ImportError, AttributeError) as exc:
        raise RuntimeError(
            f"No callable found for {app_name}.{job_name} "
            f"(expected {module_path}.execute): {exc}"
        )


# ---------------------------------------------------------------------------
# JobQueue public interface
# ---------------------------------------------------------------------------


class JobQueue:
    """
    Public interface for submitting and managing background PlatformJobs.
    """

    def submit(
        self,
        app_name: str,
        job_name: str,
        project,
        owner,
        params: Optional[Dict[str, Any]] = None,
    ):
        """Create a PlatformJob record and dispatch the Celery task."""
        from apps.infra.platform_app.models import PlatformJob

        job = PlatformJob.objects.create(
            app_name=app_name,
            job_name=job_name,
            project=project,
            owner=owner,
            params=params or {},
            status=PlatformJob.Status.QUEUED,
        )
        run_platform_job.delay(str(job.id))
        logger.info("Submitted job %s (%s.%s)", job.id, app_name, job_name)
        return job

    def status(self, job_id: str) -> Optional[Dict]:
        """Return status dict for a job, or None if not found."""
        from apps.infra.platform_app.models import PlatformJob

        try:
            job = PlatformJob.objects.get(pk=job_id)
        except PlatformJob.DoesNotExist:
            return None

        return {
            "id": str(job.id),
            "app_name": job.app_name,
            "job_name": job.job_name,
            "status": job.status,
            "progress_percent": job.progress_percent,
            "progress_message": job.progress_message,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        }

    def cancel(self, job_id: str) -> bool:
        """
        Cancel a queued or running job.

        Revokes the Celery task and marks the job as cancelled.
        Returns True if cancellation was applied, False otherwise.
        """
        from celery.app import default_app as celery_app
        from django.utils import timezone

        from apps.infra.platform_app.models import PlatformJob

        try:
            job = PlatformJob.objects.get(pk=job_id)
        except PlatformJob.DoesNotExist:
            return False

        if job.status not in (PlatformJob.Status.QUEUED, PlatformJob.Status.RUNNING):
            return False

        if job.celery_task_id:
            celery_app.control.revoke(job.celery_task_id, terminate=True)

        job.status = PlatformJob.Status.CANCELLED
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "finished_at"])
        return True

    def result(self, job_id: str) -> Optional[Dict]:
        """Return the result payload if the job completed, else None."""
        from apps.infra.platform_app.models import PlatformJob

        try:
            job = PlatformJob.objects.get(pk=job_id)
        except PlatformJob.DoesNotExist:
            return None

        if job.status == PlatformJob.Status.COMPLETED:
            return job.result
        return None

    def list_jobs(self, app_name: str, project=None, owner=None):
        """Return a QuerySet of PlatformJobs filtered by app/project/owner."""
        from apps.infra.platform_app.models import PlatformJob

        qs = PlatformJob.objects.filter(app_name=app_name)
        if project is not None:
            qs = qs.filter(project=project)
        if owner is not None:
            qs = qs.filter(owner=owner)
        return qs


# Module-level singleton for convenience
jobqueue = JobQueue()

# EOF
