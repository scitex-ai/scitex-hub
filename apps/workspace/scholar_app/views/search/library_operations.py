#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/search/library_operations.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from scitex import logging

from .citation_export_core import generate_bibtex, generate_citation_key

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
@login_required
def save_paper(request):
    """Save a search result paper to the user's project bibliography.

    Accepts paper metadata from search results:
    1. Converts to BibTeX using existing generate_bibtex()
    2. Writes .bib file to project's scitex/scholar/bib_files/
    3. Regenerates merged bibliography with deduplication
    """
    from apps.infra.project_app.models import Project
    from apps.infra.project_app.services.bibliography_manager import (
        ensure_bibliography_structure,
        regenerate_bibliography,
    )

    project_id = request.POST.get("project_id")
    if not project_id:
        return JsonResponse(
            {"success": False, "error": "No project selected"}, status=400
        )

    try:
        project = Project.objects.get(id=project_id, owner=request.user)
    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )

    if not project.git_clone_path:
        return JsonResponse(
            {"success": False, "error": "Project has no git repository"},
            status=400,
        )

    title = request.POST.get("title", "").strip()
    authors = request.POST.get("authors", "").strip()
    if not title:
        return JsonResponse(
            {"success": False, "error": "Paper title is required"}, status=400
        )

    year = request.POST.get("year", "")
    journal = request.POST.get("journal", "")
    doi = request.POST.get("doi", "")
    abstract = request.POST.get("abstract", "")
    source = request.POST.get("source", "unknown")
    url = request.POST.get("url", "")
    pmid = request.POST.get("pmid", "")

    try:
        # Extract first author's last name for citation key
        # Search results use "First Last, First Last" format
        # generate_citation_key expects "Last, First" or single name
        first_author = (authors or "Unknown").split(",")[0].strip()
        last_name = first_author.split()[-1] if first_author.split() else "Unknown"
        citation_key = generate_citation_key(last_name, year)
        bibtex_entry = generate_bibtex(
            citation_key,
            title,
            authors or "Unknown Author",
            journal,
            year,
            doi,
            url,
            "",
            "",
            pmid,
        )

        if abstract:
            bibtex_entry = (
                bibtex_entry.rstrip("}") + f"  abstract = {{{abstract}}},\n}}"
            )

        project_path = Path(project.git_clone_path)
        ensure_bibliography_structure(project_path)

        bib_dir = project_path / "scitex" / "scholar" / "bib_files"
        bib_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"search_{source}_{citation_key}_{timestamp}.bib"
        bib_file = bib_dir / filename
        bib_file.write_text(bibtex_entry, encoding="utf-8")

        logger.info(f"Saved paper to: {bib_file}")

        results = regenerate_bibliography(project_path, project.name)

        return JsonResponse(
            {
                "success": True,
                "message": f"Saved to {project.name}",
                "project": project.name,
                "citation_key": citation_key,
                "file_path": f"scitex/scholar/bib_files/{filename}",
                "total_citations": results.get("scholar_count", 0),
            }
        )

    except Exception as e:
        logger.error(f"Failed to save paper: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def save_papers_bulk(request):
    """Placeholder for save_papers_bulk - TODO: implement"""
    return JsonResponse({"error": "Not implemented"}, status=501)


@require_http_methods(["POST"])
@login_required
def upload_file(request):
    """Placeholder for upload_file - TODO: implement"""
    return JsonResponse({"error": "Not implemented"}, status=501)


@require_http_methods(["GET"])
@login_required
def get_citation(request):
    """Placeholder for get_citation - TODO: implement"""
    return JsonResponse({"error": "Not implemented"}, status=501)


@require_http_methods(["POST"])
@login_required
def mock_save_paper(request):
    """Placeholder for mock_save_paper - TODO: implement"""
    return JsonResponse({"error": "Not implemented"}, status=501)


@require_http_methods(["GET"])
@login_required
def mock_get_citation(request):
    """Placeholder for mock_get_citation - TODO: implement"""
    return JsonResponse({"error": "Not implemented"}, status=501)
