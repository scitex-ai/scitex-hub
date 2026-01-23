#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/bibtex/resource.py

"""
BibTeX Resource Status View

Monitor system resource usage and job queue status.
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from ...models import BibTeXEnrichmentJob

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def bibtex_resource_status(request):
    """AJAX endpoint to get current resource usage and job queue status."""
    import psutil

    # Get all active and queued jobs
    active_jobs = (
        BibTeXEnrichmentJob.objects.filter(status="processing")
        .select_related("user")
        .order_by("started_at")
    )

    queued_jobs = (
        BibTeXEnrichmentJob.objects.filter(status="pending")
        .select_related("user")
        .order_by("created_at")
    )

    # Get recently completed jobs (last hour)
    one_hour_ago = timezone.now() - timedelta(hours=1)

    recent_completed = BibTeXEnrichmentJob.objects.filter(
        Q(status="completed") | Q(status="failed"), completed_at__gte=one_hour_ago
    ).count()

    # Get system resource usage
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()

    # Check if current user owns any jobs
    if request.user.is_authenticated:
        user_identifier = request.user
        user_session = None
    else:
        user_identifier = None
        user_session = request.session.session_key

    # Build active jobs list (security: only show owner's jobs)
    active_jobs_list = []
    for job in active_jobs:
        is_owner = (request.user.is_authenticated and job.user == request.user) or (
            not request.user.is_authenticated
            and job.session_key == request.session.session_key
        )

        if is_owner:
            active_jobs_list.append(
                {
                    "id": str(job.id),
                    "user": "You",
                    "filename": job.original_filename or "Unknown",
                    "progress": job.get_progress_percentage(),
                    "processed": job.processed_papers,
                    "total": job.total_papers,
                    "started": job.started_at.isoformat() if job.started_at else None,
                    "can_cancel": True,
                    "is_owner": True,
                }
            )

    # Build queued jobs list with position (security: only show owner's jobs)
    queued_jobs_list = []
    user_queue_position = None
    total_queue_position = 0

    for idx, job in enumerate(queued_jobs):
        total_queue_position = idx + 1
        is_owner = (request.user.is_authenticated and job.user == request.user) or (
            not request.user.is_authenticated
            and job.session_key == request.session.session_key
        )

        if is_owner:
            user_queue_position = idx + 1
            queued_jobs_list.append(
                {
                    "id": str(job.id),
                    "user": "You",
                    "filename": job.original_filename or "Unknown",
                    "position": idx + 1,
                    "created": job.created_at.isoformat() if job.created_at else None,
                    "can_cancel": True,
                    "is_owner": True,
                }
            )

    return JsonResponse(
        {
            "system": {
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "memory_available_gb": round(memory.available / (1024**3), 2),
            },
            "jobs": {
                "active_count": active_jobs.count(),
                "queued_count": queued_jobs.count(),
                "completed_last_hour": recent_completed,
                "active": active_jobs_list,
                "queued": queued_jobs_list,
                "user_queue_position": user_queue_position,
            },
            "timestamp": timezone.now().isoformat(),
        }
    )


# EOF
