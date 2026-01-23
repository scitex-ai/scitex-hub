#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/bibtex/diff.py

"""
BibTeX Diff View

Compare original and enriched BibTeX files.
"""

import logging
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from ...models import BibTeXEnrichmentJob

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def bibtex_job_diff(request, job_id):
    """API endpoint to get diff between original and enriched BibTeX files."""
    import bibtexparser
    from apps.project_app.services.project_utils import get_current_project

    # Get the job (handle both authenticated and visitor users)
    if request.user.is_authenticated:
        try:
            job = BibTeXEnrichmentJob.objects.get(id=job_id, user=request.user)
        except BibTeXEnrichmentJob.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Job not found or access denied."},
                status=404,
            )
    else:
        # For visitor users, check by session_key
        try:
            job = BibTeXEnrichmentJob.objects.get(
                id=job_id, session_key=request.session.session_key
            )
        except BibTeXEnrichmentJob.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Job not found."}, status=404
            )

    # Check if job is completed and has output file
    if job.status != "completed":
        return JsonResponse(
            {"success": False, "error": "Job not completed yet.", "status": job.status},
            status=400,
        )

    if not job.output_file:
        return JsonResponse(
            {"success": False, "error": "No output file available."}, status=404
        )

    # Read and parse both files
    input_path = Path(settings.MEDIA_ROOT) / job.input_file.name
    output_path = Path(settings.MEDIA_ROOT) / job.output_file.name

    if not input_path.exists() or not output_path.exists():
        return JsonResponse(
            {"success": False, "error": "Input or output file not found on server."},
            status=404,
        )

    try:
        # Parse original BibTeX
        with open(input_path, "r", encoding="utf-8") as f:
            original_db = bibtexparser.load(f)

        # Parse enriched BibTeX
        with open(output_path, "r", encoding="utf-8") as f:
            enriched_db = bibtexparser.load(f)

        # Create lookup dictionaries
        original_entries = {entry["ID"]: entry for entry in original_db.entries}
        enriched_entries = {entry["ID"]: entry for entry in enriched_db.entries}

        # Calculate diff - show ALL entries
        diff = []
        for entry_id, enriched_entry in enriched_entries.items():
            original_entry = original_entries.get(entry_id, {})

            # Find added fields only
            added_fields = {}
            original_fields = {}

            for key, value in enriched_entry.items():
                if key == "ID" or key == "ENTRYTYPE":
                    continue

                original_value = original_entry.get(key, "")

                if not original_value and value:
                    # Field was added
                    added_fields[key] = value
                elif original_value:
                    # Field existed (show in original)
                    original_fields[key] = original_value

            # Convert dictionaries to arrays for frontend
            added_fields_array = [
                {"name": k, "value": v} for k, v in added_fields.items()
            ]
            original_fields_array = [
                {"name": k, "value": v} for k, v in original_fields.items()
            ]

            # Include ALL entries (even if no changes)
            diff.append(
                {
                    "key": entry_id,
                    "type": enriched_entry.get("ENTRYTYPE", "article"),
                    "title": enriched_entry.get("title", "Unknown"),
                    "unchanged_fields": original_fields_array,
                    "added_fields": added_fields_array,
                    "has_changes": len(added_fields) > 0,
                }
            )

        # Calculate statistics
        total_entries = len(enriched_entries)
        entries_enhanced = sum(1 for entry in diff if entry["has_changes"])
        total_fields_added = sum(len(entry["added_fields"]) for entry in diff)
        total_fields_modified = 0

        # Calculate major metadata success rates
        major_fields_stats = {
            "abstract": {"acquired": 0, "missing": 0},
            "doi": {"acquired": 0, "missing": 0},
            "citation_count": {"acquired": 0, "missing": 0},
            "impact_factor": {"acquired": 0, "missing": 0},
        }

        for entry_id, enriched_entry in enriched_entries.items():
            # Check abstract
            if enriched_entry.get("abstract"):
                major_fields_stats["abstract"]["acquired"] += 1
            else:
                major_fields_stats["abstract"]["missing"] += 1

            # Check DOI
            if enriched_entry.get("doi"):
                major_fields_stats["doi"]["acquired"] += 1
            else:
                major_fields_stats["doi"]["missing"] += 1

            # Check citation count
            if any(
                enriched_entry.get(field)
                for field in ["citation_count", "citations", "citationcount"]
            ):
                major_fields_stats["citation_count"]["acquired"] += 1
            else:
                major_fields_stats["citation_count"]["missing"] += 1

            # Check impact factor
            if enriched_entry.get("journal_impact_factor"):
                major_fields_stats["impact_factor"]["acquired"] += 1
            else:
                major_fields_stats["impact_factor"]["missing"] += 1

        # Build file URLs
        original_filename = job.input_file.name.split("/")[-1]
        enhanced_filename = job.output_file.name.split("/")[-1]

        # Try to build filer URLs if user is authenticated and has a project
        original_filer_url = None
        enhanced_filer_url = None

        if request.user.is_authenticated:
            try:
                current_project = get_current_project(request)
                if current_project:
                    original_filer_url = f"/{request.user.username}/{current_project.slug}/scholar/bib_files/{original_filename}"
                    enhanced_filer_url = f"/{request.user.username}/{current_project.slug}/scholar/bib_files/{enhanced_filename}"
            except Exception:
                pass

        # Fall back to download URLs
        if not original_filer_url:
            original_filer_url = f"/scholar/api/bibtex/job/{job.id}/download/original/"
        if not enhanced_filer_url:
            enhanced_filer_url = f"/scholar/api/bibtex/job/{job.id}/download/"

        return JsonResponse(
            {
                "success": True,
                "diff": diff,
                "stats": {
                    "total_entries": total_entries,
                    "entries_enhanced": entries_enhanced,
                    "total_fields_added": total_fields_added,
                    "total_fields_modified": total_fields_modified,
                    "enhancement_rate": round(
                        (entries_enhanced / total_entries * 100), 1
                    )
                    if total_entries > 0
                    else 0,
                    "major_fields": major_fields_stats,
                },
                "files": {
                    "original": original_filename,
                    "enhanced": enhanced_filename,
                    "original_url": original_filer_url,
                    "enhanced_url": enhanced_filer_url,
                },
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Failed to generate diff: {str(e)}"},
            status=500,
        )


# EOF
