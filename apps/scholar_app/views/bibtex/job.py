#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/bibtex/job.py

"""
BibTeX Job Views

Job detail, status, and paper listing endpoints.
"""

import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from pathlib import Path
from ...models import BibTeXEnrichmentJob
from apps.scholar_app.api_auth import api_key_optional

logger = logging.getLogger(__name__)


def bibtex_job_detail(request, job_id):
    """View details and progress of a BibTeX enrichment job (visitor allowed)."""
    from .utils import process_bibtex_job

    # Get job by user or session key
    if request.user.is_authenticated:
        job = get_object_or_404(BibTeXEnrichmentJob, id=job_id, user=request.user)
    else:
        job = get_object_or_404(
            BibTeXEnrichmentJob, id=job_id, session_key=request.session.session_key
        )

    # If job is pending, start processing
    if job.status == "pending":
        process_bibtex_job(job)
        job.refresh_from_db()

    context = {
        "job": job,
    }

    return render(request, "scholar_app/bibtex_job_detail.html", context)


@require_http_methods(["GET"])
@api_key_optional
def bibtex_job_status(request, job_id):
    """API endpoint to get job status and progress (supports API key auth)."""

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

    data = {
        "status": job.status,
        "progress_percentage": job.get_progress_percentage(),
        "total_papers": job.total_papers,
        "processed_papers": job.processed_papers,
        "failed_papers": job.failed_papers,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
        "has_output": bool(job.output_file),
        "log": job.processing_log,
    }

    return JsonResponse(data)


@require_http_methods(["GET"])
def bibtex_job_papers(request, job_id):
    """API endpoint to get all papers in a job as placeholders (visitor allowed)."""
    import bibtexparser

    # Get job by user or session key
    if request.user.is_authenticated:
        job = get_object_or_404(BibTeXEnrichmentJob, id=job_id, user=request.user)
    else:
        job = get_object_or_404(
            BibTeXEnrichmentJob, id=job_id, session_key=request.session.session_key
        )

    # Determine which file to read (output if completed, input otherwise)
    if job.status == "completed" and job.output_file:
        file_path = Path(settings.MEDIA_ROOT) / job.output_file.name
    else:
        file_path = Path(settings.MEDIA_ROOT) / job.input_file.name

    if not file_path.exists():
        return JsonResponse({"success": False, "error": "File not found"}, status=404)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            bib_database = bibtexparser.load(f)

        papers = []
        for entry in bib_database.entries:
            papers.append(
                {
                    "key": entry.get("ID", "Unknown"),
                    "type": entry.get("ENTRYTYPE", "article"),
                    "title": entry.get("title", "No title"),
                    "author": entry.get("author", "Unknown"),
                    "year": entry.get("year", "N/A"),
                    "journal": entry.get("journal", ""),
                    "abstract": entry.get("abstract", ""),
                    "url": entry.get("url", ""),
                    "doi": entry.get("doi", ""),
                    "citations": entry.get("citations", ""),
                    "has_abstract": bool(entry.get("abstract")),
                    "has_url": bool(entry.get("url") or entry.get("doi")),
                    "has_citations": bool(entry.get("citations")),
                }
            )

        return JsonResponse(
            {
                "success": True,
                "job_id": str(job_id),
                "total_papers": len(papers),
                "papers": papers,
                "status": job.status,
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Failed to read papers: {str(e)}"}, status=500
        )


@require_http_methods(["GET"])
def bibtex_recent_jobs(request):
    """API endpoint to get user's recent jobs with summary (visitor allowed).

    Deduplicates by content_hash, showing only the most recent job per unique file.
    """

    # Get recent jobs
    if request.user.is_authenticated:
        all_jobs = (
            BibTeXEnrichmentJob.objects.filter(user=request.user)
            .select_related("project")
            .order_by("-created_at")
        )
    else:
        # For visitor users, get jobs by session key
        all_jobs = (
            BibTeXEnrichmentJob.objects.filter(
                session_key=request.session.session_key
            ).order_by("-created_at")
            if request.session.session_key
            else BibTeXEnrichmentJob.objects.none()
        )

    # Deduplicate: keep only the most recent job per content_hash
    seen_hashes = set()
    jobs = []
    for job in all_jobs:
        # Use content_hash for deduplication, fallback to job id if no hash
        job_key = job.content_hash or str(job.id)
        if job_key not in seen_hashes:
            seen_hashes.add(job_key)
            jobs.append(job)
            if len(jobs) >= 10:
                break

    jobs_data = []
    for job in jobs:
        jobs_data.append(
            {
                "id": str(job.id),
                "original_filename": job.original_filename or "Unknown",
                "status": job.status,
                "total_papers": job.total_papers,
                "processed_papers": job.processed_papers,
                "failed_papers": job.failed_papers,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat()
                if job.completed_at
                else None,
                "progress_percentage": job.get_progress_percentage(),
                "project_name": job.project.name if job.project else None,
            }
        )

    return JsonResponse(
        {
            "success": True,
            "jobs": jobs_data,
            "total": len(jobs_data),
        }
    )


# EOF
