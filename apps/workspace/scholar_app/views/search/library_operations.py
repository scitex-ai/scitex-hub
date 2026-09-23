#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-hub/apps/scholar_app/views/search/library_operations.py
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from scitex import logging

from .citation_export_core import generate_bibtex, generate_citation_key

logger = logging.getLogger(__name__)


def get_user_scholar_library(username: str) -> Path:
    """User-scope Scholar library dir (~/.scitex/scholar/library).

    Root is SCITEX_USER_DATA_ROOT (/app/data/users default), which the
    user container mounts as /home/user — hence the ~/.scitex view.
    """
    root = Path(os.environ.get("SCITEX_USER_DATA_ROOT", "/app/data/users"))
    return root / username / ".scitex" / "scholar" / "library"


@require_http_methods(["POST"])
@login_required
def save_paper(request):
    """Save a search result paper to the user's Scholar library (user scope).

    Storage model (single source of truth + symlinks):
    1. Converts to BibTeX using existing generate_bibtex()
    2. Writes the canonical .bib file to the USER library:
       /app/data/users/<username>/.scitex/scholar/library/
       (the user sees this as ~/.scitex/scholar/library).
       Same DOI saved twice reuses the existing file (no duplicates).
    3. If project_id is given, links it into the project instead of copying:
       <project>/scitex/scholar/bib_files/<filename> -> relative symlink
       to the user-library file. Relative so it resolves under both the
       /app/data/users/... (hub) and /home/user/... (user container) views.
    4. Regenerates the project's merged bibliography (follows symlinks).
    """
    from apps.infra.project_app.models import Project
    from apps.infra.project_app.services.bibliography_manager import (
        ensure_bibliography_structure,
        regenerate_bibliography,
    )

    project_id = request.POST.get("project_id") or None
    project = None
    if project_id:
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

        # 1. Canonical copy: user-scope Scholar library (~/.scitex/scholar/library)
        user_lib = get_user_scholar_library(request.user.username)
        user_lib.mkdir(parents=True, exist_ok=True)

        slug = "".join(
            c.lower() if (c.isalnum() or c in "-_") else "-"
            for c in citation_key
        ).strip("-") or "paper"
        if doi:
            dedupe_tag = "doi-" + "".join(
                c.lower() if c.isalnum() else "-"
                for c in doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
            ).strip("-")
        else:
            dedupe_tag = slug
        canonical = None
        for existing in user_lib.glob(f"*-{dedupe_tag}.bib"):
            canonical = existing
            break
        if canonical is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            canonical = user_lib / f"{timestamp}-{dedupe_tag}.bib"
            canonical.write_text(bibtex_entry, encoding="utf-8")
            logger.info(f"Saved paper to user library: {canonical}")
        else:
            logger.info(f"Paper already in user library: {canonical}")

        file_rel = None
        total = None
        if project is not None:
            project_path = Path(project.git_clone_path)
            ensure_bibliography_structure(project_path)

            bib_dir = project_path / "scitex" / "scholar" / "bib_files"
            bib_dir.mkdir(parents=True, exist_ok=True)

            # 2. Project scope: symlink (never a copy) to the canonical file.
            # Relative so it resolves under both /app/data/users/... (hub)
            # and /home/user/... (user container) views.
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            link_name = f"search_{source}_{slug}_{timestamp}.bib"
            link_path = bib_dir / link_name
            target_rel = Path(os.path.relpath(canonical, start=bib_dir))
            if link_path.is_symlink() or link_path.exists():
                link_path.unlink()
            link_path.symlink_to(target_rel)
            logger.info(f"Linked paper into project: {link_path} -> {target_rel}")

            results = regenerate_bibliography(project_path, project.name)
            file_rel = f"scitex/scholar/bib_files/{link_name}"
            total = results.get("scholar_count", 0)

        return JsonResponse(
            {
                "success": True,
                "message": f"Saved to {'project ' + project.name if project else 'your library'}",
                "project": project.name if project else None,
                "citation_key": citation_key,
                "library_path": f"~/.scitex/scholar/library/{canonical.name}",
                "file_path": file_rel,
                "total_citations": total,
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
