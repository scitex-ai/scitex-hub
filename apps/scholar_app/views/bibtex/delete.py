#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/bibtex/delete.py

"""
BibTeX Job Deletion View

Delete completed or failed enrichment jobs from the database.
"""

import logging
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ...models import BibTeXEnrichmentJob

logger = logging.getLogger(__name__)


@require_http_methods(["DELETE"])
def bibtex_delete_job(request, job_id):
    """Delete a BibTeX enrichment job from the database."""

    # Get job by user or session key
    if request.user.is_authenticated:
        job = get_object_or_404(BibTeXEnrichmentJob, id=job_id, user=request.user)
    else:
        job = get_object_or_404(
            BibTeXEnrichmentJob, id=job_id, session_key=request.session.session_key
        )

    # Don't allow deleting jobs that are currently processing
    if job.status == "processing":
        return JsonResponse(
            {"success": False, "error": "Cannot delete job that is currently processing. Cancel it first."},
            status=400,
        )

    # Delete the job
    job_status = job.status
    job.delete()

    logger.info(f"Deleted BibTeX job {job_id} with status {job_status}")

    return JsonResponse({"success": True, "message": "Job deleted successfully"})


# EOF
