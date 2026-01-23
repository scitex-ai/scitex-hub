#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/bibtex/upload.py

"""
BibTeX Upload View

Handle BibTeX file upload and start enrichment job.
"""

import logging
import hashlib
from pathlib import Path
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from ...models import BibTeXEnrichmentJob
from apps.scholar_app.api_auth import api_key_optional

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
@api_key_optional
def bibtex_upload(request):
    """Handle BibTeX file upload and start enrichment job (supports API key auth)."""

    # Check for API key authentication
    api_authenticated = hasattr(request, "api_user")

    # Get authenticated user (from API key or session)
    if api_authenticated:
        user = request.api_user
        is_authenticated = True
    else:
        user = request.user
        is_authenticated = request.user.is_authenticated

        # Ensure session exists for visitor users
        if not is_authenticated and not request.session.session_key:
            request.session.create()

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

    # Job management: One user = One job at a time
    if is_authenticated:
        # Authenticated users: Can cancel old jobs and start new ones
        existing_jobs = BibTeXEnrichmentJob.objects.filter(
            user=user, status__in=["pending", "processing"]
        )

        # Cancel all existing jobs - new upload takes priority
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

    else:
        # Visitor users: Ask if they want to cancel old job
        existing_jobs = (
            BibTeXEnrichmentJob.objects.filter(
                session_key=request.session.session_key,
                status__in=["pending", "processing"],
            )
            if request.session.session_key
            else BibTeXEnrichmentJob.objects.none()
        )

        if existing_jobs.exists():
            # Check if user explicitly wants to cancel old job
            force_cancel = request.POST.get("force_cancel") == "true"

            if force_cancel:
                # User chose to cancel old job - proceed with cancellation
                for old_job in existing_jobs:
                    old_job.status = "cancelled"
                    old_job.error_message = "Cancelled - new job uploaded"
                    old_job.completed_at = timezone.now()
                    old_job.processing_log += (
                        "\n\n✗ Cancelled by user uploading new file"
                    )
                    old_job.save(
                        update_fields=[
                            "status",
                            "error_message",
                            "completed_at",
                            "processing_log",
                        ]
                    )
            else:
                # Show confirmation dialog to user
                existing_job = existing_jobs.first()
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": False,
                            "requires_confirmation": True,
                            "existing_job": {
                                "id": str(existing_job.id),
                                "filename": existing_job.original_filename or "Unknown",
                                "progress": existing_job.get_progress_percentage(),
                                "status": existing_job.status,
                            },
                            "message": "You already have a job in progress. Cancel it and start new job?",
                        },
                        status=409,
                    )
                else:
                    messages.warning(
                        request,
                        f'You already have a job in progress: "{existing_job.original_filename or "Unknown"}". Please wait for it to complete.',
                    )
                    return redirect("scholar_app:bibtex_enrichment")

    # Get optional parameters
    project_name = request.POST.get("project_name", "").strip() or None
    project_id = request.POST.get("project_id", "").strip() or None
    num_workers = int(request.POST.get("num_workers", 4))
    browser_mode = request.POST.get("browser_mode", "stealth")
    use_cache = request.POST.get("use_cache", "on") == "on"

    # Get project if specified (for authenticated users or visitors with assigned project)
    project = None
    if project_id:
        from apps.project_app.models import Project

        try:
            if is_authenticated:
                # Authenticated user - must own the project
                project = Project.objects.get(id=project_id, owner=user)
            else:
                # Visitor user - check if this is their assigned project from pool
                from apps.project_app.services.visitor_pool import VisitorPool
                visitor_project_id = request.session.get(VisitorPool.SESSION_KEY_PROJECT_ID)
                if visitor_project_id and str(visitor_project_id) == str(project_id):
                    project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            if api_authenticated:
                return JsonResponse(
                    {"success": False, "error": "Project not found"}, status=404
                )
            messages.error(request, "Selected project not found.")
            return redirect("scholar_app:bibtex_enrichment")

    # Save uploaded file - use user ID or session key
    if is_authenticated:
        user_identifier = str(user.id)
    else:
        user_identifier = f"visitor_{request.session.session_key}"

    file_content = bibtex_file.read()

    # Compute content hash for deduplication
    content_hash = hashlib.sha256(file_content).hexdigest()

    # Check for duplicate: same user + same content hash + completed job
    if is_authenticated:
        existing_completed = BibTeXEnrichmentJob.objects.filter(
            user=user,
            content_hash=content_hash,
            status="completed",
        ).order_by("-completed_at").first()
    else:
        existing_completed = BibTeXEnrichmentJob.objects.filter(
            session_key=request.session.session_key,
            content_hash=content_hash,
            status="completed",
        ).order_by("-completed_at").first() if request.session.session_key else None

    if existing_completed:
        # Return cached result instead of re-processing
        if api_authenticated or request.headers.get("X-Requested-With") == "XMLHttpRequest":
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
        messages.info(request, "This file was already enriched. Returning cached result.")
        return redirect("scholar_app:bibtex_job_detail", job_id=existing_completed.id)

    file_path = default_storage.save(
        f"bibtex_uploads/{user_identifier}/{bibtex_file.name}",
        ContentFile(file_content),
    )

    # Also save uploaded file to project's bib_files directory if project exists
    if project and project.git_clone_path:
        try:
            import shutil
            from datetime import datetime
            from django.conf import settings

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
        user=user if is_authenticated else None,
        session_key=request.session.session_key if not is_authenticated else None,
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
