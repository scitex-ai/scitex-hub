#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Console App SLURM Job API URLs

REST API endpoints for SLURM job management:
- Job submission
- Job status, output, cancellation
- Queue status
- User job listing
"""

from django.urls import path

from .. import job_api_views

urlpatterns = [
    # SLURM job management API
    path("api/jobs/submit/", job_api_views.api_submit_job, name="api_submit_job"),
    path(
        "api/jobs/<int:job_id>/status/",
        job_api_views.api_job_status,
        name="api_job_status_slurm",
    ),
    path(
        "api/jobs/<int:job_id>/cancel/",
        job_api_views.api_cancel_job,
        name="api_cancel_job",
    ),
    path(
        "api/jobs/<int:job_id>/output/",
        job_api_views.api_job_output,
        name="api_job_output",
    ),
    path("api/jobs/queue/", job_api_views.api_queue_status, name="api_queue_status"),
    path("api/jobs/", job_api_views.api_user_jobs, name="api_user_jobs"),
]

# EOF
