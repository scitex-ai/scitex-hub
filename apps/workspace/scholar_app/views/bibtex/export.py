#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/bibtex/export.py

"""
BibTeX Export Views

URL extraction and save to project functionality.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.workspace.scholar_app.api_auth import api_key_optional

from ...models import BibTeXEnrichmentJob

logger = logging.getLogger(__name__)


def bibtex_get_urls(request, job_id):
    """API endpoint to extract URLs and DOIs from enriched BibTeX file."""
    import bibtexparser

    # Get the job (handle both authenticated and visitor users)
    if request.user.is_authenticated:
        try:
            job = BibTeXEnrichmentJob.objects.get(id=job_id, user=request.user)
        except BibTeXEnrichmentJob.DoesNotExist:
            return JsonResponse(
                {"error": "Job not found or access denied."}, status=404
            )
    else:
        # For visitor users, check by session_key
        try:
            job = BibTeXEnrichmentJob.objects.get(
                id=job_id, session_key=request.session.session_key
            )
        except BibTeXEnrichmentJob.DoesNotExist:
            return JsonResponse({"error": "Job not found."}, status=404)

    # Check if job is completed and has output file
    if job.status != "completed":
        return JsonResponse(
            {"error": "Job not completed yet.", "status": job.status}, status=400
        )

    if not job.output_file:
        return JsonResponse({"error": "No output file available."}, status=404)

    # Read and parse the BibTeX file
    file_path = Path(settings.MEDIA_ROOT) / job.output_file.name
    if not file_path.exists():
        return JsonResponse({"error": "Output file not found on server."}, status=404)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            bib_database = bibtexparser.load(f)

        urls = []
        for entry in bib_database.entries:
            title = entry.get("title", "Unknown")
            doi = entry.get("doi", "").strip()
            url = entry.get("url", "").strip()

            # Prioritize DOI over URL
            if doi:
                # Add https://doi.org/ prefix if not already present
                if not doi.startswith("http"):
                    final_url = f"https://doi.org/{doi}"
                else:
                    final_url = doi
                urls.append({"title": title, "url": final_url, "type": "doi"})
            elif url:
                urls.append({"title": title, "url": url, "type": "url"})

        return JsonResponse(
            {"job_id": str(job_id), "total_urls": len(urls), "urls": urls}
        )

    except Exception as e:
        return JsonResponse({"error": f"Failed to extract URLs: {str(e)}"}, status=500)


@require_http_methods(["POST"])
@api_key_optional
def bibtex_save_to_project(request, job_id):
    """Save enriched BibTeX to selected project."""

    # Get authenticated user
    api_authenticated = hasattr(request, "api_user")
    user = request.api_user if api_authenticated else request.user

    if not user or not user.is_authenticated:
        return JsonResponse(
            {"success": False, "error": "Authentication required"}, status=401
        )

    # Get job
    try:
        job = BibTeXEnrichmentJob.objects.get(id=job_id, user=user)
    except BibTeXEnrichmentJob.DoesNotExist:
        return JsonResponse({"success": False, "error": "Job not found"}, status=404)

    if job.status != "completed":
        return JsonResponse(
            {"success": False, "error": f"Job not completed (status: {job.status})"},
            status=400,
        )

    # Get project_id from request
    project_id = request.POST.get("project_id")
    if not project_id:
        return JsonResponse(
            {"success": False, "error": "No project selected"}, status=400
        )

    # Get project
    from apps.infra.project_app.models import Project

    try:
        project = Project.objects.get(id=project_id, owner=user)
    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )

    try:
        # Validate job has required files
        if not job.input_file or not job.input_file.name:
            logger.error(f"Job {job_id} has no input file")
            return JsonResponse(
                {"success": False, "error": "Original BibTeX file not found"},
                status=404,
            )

        if not job.output_file or not job.output_file.name:
            logger.error(f"Job {job_id} has no output file")
            return JsonResponse(
                {
                    "success": False,
                    "error": "Enriched BibTeX file not found. Job may not be completed yet.",
                },
                status=404,
            )

        # Generate filenames
        original_name = (
            Path(job.original_filename).stem if job.original_filename else "references"
        )
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        # Copy source files
        input_path = Path(settings.MEDIA_ROOT) / job.input_file.name
        output_path = Path(settings.MEDIA_ROOT) / job.output_file.name

        logger.info(f"Save to project - Input: {input_path}, Output: {output_path}")

        # Validate paths exist
        if not input_path.exists() or not input_path.is_file():
            logger.error(
                f"Input path invalid: exists={input_path.exists()}, is_file={input_path.is_file()}"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": "Original BibTeX file not found at expected location",
                },
                status=404,
            )

        if not output_path.exists() or not output_path.is_file():
            logger.error(
                f"Output path invalid: exists={output_path.exists()}, is_file={output_path.is_file()}"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": "Enriched BibTeX file not found at expected location",
                },
                status=404,
            )

        original_filename = f"{original_name}_original-{timestamp}.bib"
        enriched_filename = f"{original_name}_enriched-{timestamp}.bib"

        committed = False

        # If project has git repository, save to git and commit
        if project.git_clone_path:
            from apps.infra.project_app.services.bibliography_manager import (
                ensure_bibliography_structure,
                regenerate_bibliography,
            )

            # Create directory in git repo
            project_bib_dir = (
                Path(project.git_clone_path) / "scitex" / "scholar" / "bib_files"
            )
            project_bib_dir.mkdir(parents=True, exist_ok=True)

            # Copy both files to git directory
            shutil.copy(input_path, project_bib_dir / original_filename)
            shutil.copy(output_path, project_bib_dir / enriched_filename)

            # Regenerate bibliography
            project_path = Path(project.git_clone_path)
            ensure_bibliography_structure(project_path)
            results = regenerate_bibliography(project_path, project.name)

            if results["success"]:
                logger.info(
                    f"Bibliography regenerated: "
                    f"scholar={results['scholar_count']}, "
                    f"duplicates_removed={results.get('duplicates_removed', 0)}"
                )
            else:
                logger.warning(
                    f"Bibliography regeneration had errors: {results['errors']}"
                )

            # Auto-commit disabled - users should commit manually when ready
            # Changes will show in git gutter until committed
            committed = False

        else:
            # Fallback: Save to media directory
            project_media_dir = (
                Path(settings.MEDIA_ROOT)
                / "projects"
                / str(project.id)
                / "scholar"
                / "bib_files"
            )
            project_media_dir.mkdir(parents=True, exist_ok=True)

            # Copy both files
            shutil.copy(input_path, project_media_dir / original_filename)
            shutil.copy(output_path, project_media_dir / enriched_filename)

        # Build file paths for response
        if project.git_clone_path:
            file_paths = {
                "original": f"scitex/scholar/bib_files/{original_filename}",
                "enriched": f"scitex/scholar/bib_files/{enriched_filename}",
                "merged": "scitex/scholar/references.bib",
            }
        else:
            file_paths = {
                "original": f"projects/{project.id}/scholar/bib_files/{original_filename}",
                "enriched": f"projects/{project.id}/scholar/bib_files/{enriched_filename}",
            }

        return JsonResponse(
            {
                "success": True,
                "message": f"Saved to {project.name}",
                "project": project.name,
                "committed": committed,
                "storage": "git" if project.git_clone_path else "media",
                "paths": file_paths,
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Save failed: {str(e)}"}, status=500
        )


# EOF
