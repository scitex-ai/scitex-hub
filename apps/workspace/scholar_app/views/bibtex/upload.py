#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-hub/apps/scholar_app/views/bibtex/upload.py

"""
BibTeX Upload View

Handle BibTeX file upload and start enrichment job.
"""

import hashlib
import logging
from pathlib import Path

from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.workspace.scholar_app.api_auth import api_key_optional

from ...models import BibTeXEnrichmentJob

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
@api_key_optional
def bibtex_upload(request):
    """Handle BibTeX file upload and start enrichment job (supports API key auth)."""

    # Check for API key authentication
    api_authenticated = hasattr(request, "api_user")

    if api_authenticated:
        user = request.api_user
    else:
        if not request.user.is_authenticated:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Authentication required. Sign up or log in.",
                        "signup_url": "/auth/signup/",
                    },
                    status=401,
                )
            return redirect("auth_app:signup")
        user = request.user

    # Check if file was uploaded
    if "bibtex_file" not in request.FILES:
        if (
            api_authenticated
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": "No file uploaded",
                    "detail": "Include bibtex_file in request",
                },
                status=400,
            )
        messages.error(request, "Please select a BibTeX file to upload.")
        return redirect("scholar_app:bibtex_enrichment")

    bibtex_file = request.FILES["bibtex_file"]

    # Store original filename (before Django adds suffix)
    original_filename = bibtex_file.name

    # Validate file extension
    if not bibtex_file.name.endswith(".bib"):
        messages.error(request, "Please upload a .bib file.")
        return redirect("scholar_app:bibtex_enrichment")

    # One authenticated user has one active job at a time; a new upload wins.
    existing_jobs = BibTeXEnrichmentJob.objects.filter(
        user=user, status__in=["pending", "processing"]
    )
    for old_job in existing_jobs:
        old_job.status = "cancelled"
        old_job.error_message = "Cancelled - new job uploaded"
        old_job.completed_at = timezone.now()
        old_job.processing_log += "\n\n✗ Cancelled by user uploading new file"
        old_job.save(
            update_fields=[
                "status",
                "error_message",
                "completed_at",
                "processing_log",
            ]
        )

    # Get optional parameters
    project_name = request.POST.get("project_name", "").strip() or None
    project_id = request.POST.get("project_id", "").strip() or None
    num_workers = int(request.POST.get("num_workers", 4))
    browser_mode = request.POST.get("browser_mode", "stealth")
    use_cache = request.POST.get("use_cache", "on") == "on"

    # A selected project must belong to the authenticated caller.
    project = None
    if project_id:
        from apps.infra.project_app.models import Project

        try:
            project = Project.objects.get(id=project_id, owner=user)
        except Project.DoesNotExist:
            if api_authenticated:
                return JsonResponse(
                    {"success": False, "error": "Project not found"}, status=404
                )
            messages.error(request, "Selected project not found.")
            return redirect("scholar_app:bibtex_enrichment")

    user_identifier = str(user.id)

    file_content = bibtex_file.read()

    # Compute content hash for deduplication
    content_hash = hashlib.sha256(file_content).hexdigest()

    # Check for duplicate: same user + same content hash + completed job
    existing_completed = (
        BibTeXEnrichmentJob.objects.filter(
            user=user,
            content_hash=content_hash,
            status="completed",
        )
        .order_by("-completed_at")
        .first()
    )

    if existing_completed:
        # Return cached result instead of re-processing
        if (
            api_authenticated
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        ):
            return JsonResponse(
                {
                    "success": True,
                    "cached": True,
                    "job_id": str(existing_completed.id),
                    "status": "completed",
                    "message": "This file was already enriched. Returning cached result.",
                    "api_endpoints": {
                        "status": f"/scholar/api/bibtex/job/{existing_completed.id}/status/",
                        "download": f"/scholar/api/bibtex/job/{existing_completed.id}/download/",
                        "papers": f"/scholar/api/bibtex/job/{existing_completed.id}/papers/",
                    },
                }
            )
        messages.info(
            request, "This file was already enriched. Returning cached result."
        )
        return redirect("scholar_app:bibtex_job_detail", job_id=existing_completed.id)

    file_path = default_storage.save(
        f"bibtex_uploads/{user_identifier}/{bibtex_file.name}",
        ContentFile(file_content),
    )

    # Also save uploaded file to project's bib_files directory if project exists
    if project and project.git_clone_path:
        try:
            from datetime import datetime


            # Create bib_files directory in project
            project_bib_dir = (
                Path(project.git_clone_path) / "scitex" / "scholar" / "bib_files"
            )
            project_bib_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename_stem = Path(original_filename).stem
            uploaded_filename = f"{filename_stem}_uploaded-{timestamp}.bib"

            # Save the uploaded file to project
            uploaded_file_path = project_bib_dir / uploaded_filename
            uploaded_file_path.write_bytes(file_content)

            logger.info(
                f"Saved uploaded file to project: {uploaded_file_path.relative_to(project.git_clone_path)}"
            )

        except Exception as e:
            logger.warning(f"Failed to save uploaded file to project: {e}")
            # Don't fail the upload if project save fails

    # Create enrichment job
    job = BibTeXEnrichmentJob.objects.create(
        user=user,
        session_key=None,
        input_file=file_path,
        original_filename=original_filename,
        content_hash=content_hash,
        project_name=project_name,
        project=project,
        num_workers=num_workers,
        browser_mode=browser_mode,
        use_cache=use_cache,
        status="pending",
    )

    # Start processing immediately in a background thread
    import threading

    from .utils import process_bibtex_job

    thread = threading.Thread(target=process_bibtex_job, args=(job,))
    thread.daemon = True
    thread.start()

    # Return JSON for API and AJAX requests
    if api_authenticated or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": True,
                "job_id": str(job.id),
                "status": "pending",
                "message": "Enrichment job started",
                "api_endpoints": {
                    "status": f"/scholar/api/bibtex/job/{job.id}/status/",
                    "download": f"/scholar/api/bibtex/job/{job.id}/download/",
                    "papers": f"/scholar/api/bibtex/job/{job.id}/papers/",
                },
            }
        )

    return redirect("scholar_app:bibtex_job_detail", job_id=job.id)


# EOF
