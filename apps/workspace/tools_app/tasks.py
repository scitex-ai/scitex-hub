"""Celery tasks for the Tools app."""

from __future__ import annotations

from celery import shared_task


@shared_task(name="apps.workspace.tools_app.tasks.x2pdf_convert", soft_time_limit=240, time_limit=300)
def x2pdf_convert(user_id: int, job_id: str) -> str:
    from django.contrib.auth import get_user_model

    from .x2pdf.jobs import job_dir, run_job

    user = get_user_model().objects.get(pk=user_id)
    path = job_dir(user, job_id)
    if path is None:
        return "missing"
    return run_job(path).get("status", "error")
