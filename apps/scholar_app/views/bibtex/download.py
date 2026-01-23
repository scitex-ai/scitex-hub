#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/bibtex/download.py

"""
BibTeX Download Views

Download original and enriched BibTeX files.
"""

import logging
from pathlib import Path
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.conf import settings
from ...models import BibTeXEnrichmentJob
from apps.scholar_app.api_auth import api_key_optional

logger = logging.getLogger(__name__)


@api_key_optional
def bibtex_download_enriched(request, job_id):
    """Download the enriched BibTeX file (supports API key auth)."""

    # Check for API key authentication
    api_authenticated = hasattr(request, "api_user")
    user = request.api_user if api_authenticated else request.user

    # Get job by user or session key
    if api_authenticated or request.user.is_authenticated:
        job = get_object_or_404(BibTeXEnrichmentJob, id=job_id, user=user)
    else:
        job = get_object_or_404(
            BibTeXEnrichmentJob, id=job_id, session_key=request.session.session_key
        )

    if job.status != "completed" or not job.output_file:
        if api_authenticated:
            return JsonResponse(
                {
                    "success": False,
                    "error": "File not ready",
                    "detail": f"Job status: {job.status}",
                    "job_id": str(job_id),
                },
                status=400,
            )
        messages.error(request, "Enriched BibTeX file not available yet.")
        return redirect("scholar_app:bibtex_job_detail", job_id=job_id)

    # Serve the file
    file_path = Path(settings.MEDIA_ROOT) / job.output_file.name

    if not file_path.exists():
        if api_authenticated:
            return JsonResponse(
                {"success": False, "error": "File not found on server"}, status=404
            )
        messages.error(request, "File not found.")
        return redirect("scholar_app:bibtex_job_detail", job_id=job_id)

    response = FileResponse(open(file_path, "rb"), content_type="application/x-bibtex")
    response["Content-Disposition"] = f'attachment; filename="{file_path.name}"'

    return response


def bibtex_download_original(request, job_id):
    """Download the original BibTeX file (supports API key auth)."""

    # Check for API key authentication
    api_authenticated = hasattr(request, "api_user")
    user = request.api_user if api_authenticated else request.user

    # Get job by user or session key
    if api_authenticated or request.user.is_authenticated:
        job = get_object_or_404(BibTeXEnrichmentJob, id=job_id, user=user)
    else:
        job = get_object_or_404(
            BibTeXEnrichmentJob, id=job_id, session_key=request.session.session_key
        )

    if not job.input_file:
        if api_authenticated:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Original file not available",
                    "job_id": str(job_id),
                },
                status=400,
            )
        messages.error(request, "Original BibTeX file not available.")
        return redirect("scholar_app:bibtex_job_detail", job_id=job_id)

    # Serve the file
    file_path = Path(settings.MEDIA_ROOT) / job.input_file.name

    if not file_path.exists():
        if api_authenticated:
            return JsonResponse(
                {"success": False, "error": "File not found on server"}, status=404
            )
        messages.error(request, "File not found.")
        return redirect("scholar_app:bibtex_job_detail", job_id=job_id)

    response = FileResponse(open(file_path, "rb"), content_type="application/x-bibtex")
    response["Content-Disposition"] = f'attachment; filename="{file_path.name}"'

    return response


# EOF
