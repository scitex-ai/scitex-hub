#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/bibtex/cancel.py

"""
BibTeX Job Cancellation View

Cancel running or queued enrichment jobs.
"""

import logging
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from ...models import BibTeXEnrichmentJob

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def bibtex_cancel_job(request, job_id):
    """Cancel a running or queued BibTeX enrichment job."""

    # Get job by user or session key
    if request.user.is_authenticated:
        job = get_object_or_404(BibTeXEnrichmentJob, id=job_id, user=request.user)
    else:
        job = get_object_or_404(
            BibTeXEnrichmentJob, id=job_id, session_key=request.session.session_key
        )

    # Only allow cancelling pending or processing jobs
    if job.status not in ["pending", "processing"]:
        return JsonResponse(
            {"success": False, "error": f"Cannot cancel job with status: {job.status}"},
            status=400,
        )

    # Mark job as cancelled
    job.status = "cancelled"
    job.error_message = "Cancelled by user"
    job.completed_at = timezone.now()
    job.processing_log += "\n\n✗ Job cancelled by user"
    job.save(
        update_fields=["status", "error_message", "completed_at", "processing_log"]
    )

    return JsonResponse({"success": True, "message": "Job cancelled successfully"})


# EOF
