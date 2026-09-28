#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-hub/apps/scholar_app/views/search/library_operations.py
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from scitex import logging

from .citation_export_core import generate_bibtex, generate_citation_key

logger = logging.getLogger(__name__)

#: Maximum papers accepted in a single bulk-save request.
BULK_SAVE_LIMIT = 200


def _resolve_save_project(user, ref):
    """Resolve a save target: numeric id (owned) or owner/slug (accessible).

    The web selector posts numeric ids; deep links and the normalized
    project context may carry owner/slug. A ref that resolves to nothing
    returns None (callers answer 404) instead of raising into a 500.
    """
    from apps.infra.project_app.models import Project
    from apps.infra.project_app.services.project_scope import (
        find_accessible_project,
    )

    ref = str(ref).strip()
    if ref.isdigit():
        return Project.objects.filter(id=int(ref), owner=user).first()
    return find_accessible_project(user, ref)


def build_bibtex_for_paper(paper: Mapping[str, Any]) -> tuple[str, str]:
    """Build (citation_key, bibtex_entry) for one search-result paper.

    Pure function (no DB, no filesystem) so it is unit-testable.
    Raises ValueError when the paper has no usable title.
    """
    from .text_clean import clean_text as _clean_text

    title = _clean_text(paper.get("title", "") or "")
    authors = _clean_text(paper.get("authors", "") or "")
    if not title:
        raise ValueError("Paper title is required")

    year = paper.get("year", "") or ""
    journal = _clean_text(paper.get("journal", "") or "")
    doi = paper.get("doi", "") or ""
    abstract = _clean_text(paper.get("abstract", "") or "")
    url = paper.get("url", "") or paper.get("externalUrl", "") or ""
    pmid = paper.get("pmid", "") or ""

    # Search results use "First Last, First Last" format;
    # generate_citation_key expects "Last, First" or single name.
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

    return citation_key, bibtex_entry


def _write_paper_bib(
    project_path: Path, source: str, citation_key: str, bibtex_entry: str
) -> str:
    """Write one .bib file under the project's bib_files dir. Returns filename."""
    import uuid

    bib_dir = project_path / "scitex" / "scholar" / "bib_files"
    bib_dir.mkdir(parents=True, exist_ok=True)

    safe_source = "".join(
        c if (c.isalnum() or c in ("-", "_")) else "_" for c in str(source)
    )[:24]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique = uuid.uuid4().hex[:6]
    filename = f"search_{safe_source}_{citation_key}_{timestamp}_{unique}.bib"
    (bib_dir / filename).write_text(bibtex_entry, encoding="utf-8")
    return filename


def _save_papers_to_project_path(
    project_path: Path, project_name: str, papers: list
) -> dict:
    """Write .bib files for every valid paper, regenerate once, summarize.

    Papers without a title are skipped (reported in ``errors``) instead of
    aborting the whole batch. Filesystem-only: no DB access.
    """
    from apps.infra.project_app.services.bibliography_manager import (
        ensure_bibliography_structure,
        regenerate_bibliography,
    )

    project_path = Path(project_path)
    ensure_bibliography_structure(project_path)

    saved = 0
    skipped = 0
    errors: list = []
    files: list = []

    for index, paper in enumerate(papers or []):
        if not isinstance(paper, dict):
            skipped += 1
            errors.append(
                {"index": index, "title": "", "error": "Paper entry is not an object"}
            )
            continue
        try:
            citation_key, bibtex_entry = build_bibtex_for_paper(paper)
        except ValueError as e:
            skipped += 1
            errors.append(
                {"index": index, "title": paper.get("title", ""), "error": str(e)}
            )
            continue

        source = paper.get("source", "") or "unknown"
        filename = _write_paper_bib(
            project_path, source, citation_key, bibtex_entry
        )
        logger.info(f"Saved paper to: {project_path / filename}")
        saved += 1
        files.append(
            {
                "citation_key": citation_key,
                "file_path": f"scitex/scholar/bib_files/{filename}",
            }
        )

    total_citations = 0
    bibliography_warning = ""
    if saved:
        results = regenerate_bibliography(project_path, project_name)
        total_citations = results.get("scholar_count", 0)
        if not results.get("success", True):
            # Papers are saved (per-paper .bibs); only the merged convenience
            # bib failed — loud warning, never a silent 500 of good saves.
            bibliography_warning = "; ".join(results.get("errors", []))[:500]
            logger.warning(
                f"Bibliography merge failed after saving {saved} papers: "
                f"{bibliography_warning}"
            )

    return {
        "saved": saved,
        "skipped": skipped,
        "errors": errors,
        "files": files,
        "total_citations": total_citations,
        "bibliography_warning": bibliography_warning,
    }


def _mirror_to_user_library(user, project_path, items) -> int:
    """Mirror saved papers into the user's package-layout home library.

    Thin-layer glue: project .bibs (written by callers) stay the manuscript
    source of truth; this additionally registers each paper under
    ``MASTER/<paper_id>/`` (bib + package-schema metadata.json, no PDF from
    search results) and ensures the
    ``<project>/.scitex/scholar/library`` tree link. Best-effort: failures
    are logged and never fail the save.

    Args:
        user: Django User
        project_path: project root (for the tree link)
        items: iterable of (paper_dict, citation_key, bibtex_entry)

    Returns:
        Number of papers registered.
    """
    try:
        from apps.workspace.scholar_app.services import UserLibraryService
    except ImportError:
        return 0
    registered = 0
    try:
        lib = UserLibraryService(user)
        for paper, citation_key, bibtex_entry in items:
            if not isinstance(paper, dict):
                continue
            doi = (paper.get("doi") or "").strip()
            arxiv = (paper.get("arxiv") or paper.get("arxiv_id") or "").strip()
            pmid = (paper.get("pmid") or "").strip()
            if doi:
                identifier, id_type = doi, "doi"
            elif arxiv:
                identifier, id_type = arxiv, "arxiv"
            elif pmid:
                identifier, id_type = pmid, "pmid"
            else:
                identifier, id_type = citation_key, "web"
            raw_authors = paper.get("authors", "") or ""
            authors = [a.strip() for a in str(raw_authors).split(",") if a.strip()]
            try:
                year = int(str(paper.get("year", "")).strip()[:4])
            except (ValueError, TypeError):
                year = None
            lib.add_paper(
                identifier,
                id_type,
                bibtex_content=bibtex_entry,
                metadata={
                    "id": {
                        "doi": doi or None,
                        "arxiv_id": arxiv or None,
                        "pmid": pmid or None,
                    },
                    "basic": {
                        "title": paper.get("title"),
                        "year": year,
                        "authors": authors,
                        "abstract": paper.get("abstract"),
                    },
                    "publication": {"journal": paper.get("journal")},
                },
            )
            registered += 1
        lib.ensure_project_link(Path(project_path))
    except Exception as e:
        logger.warning(f"User-library mirror skipped: {e}")
    return registered


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

    project = _resolve_save_project(request.user, project_id)
    if project is None:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )

    if not project.git_clone_path:
        return JsonResponse(
            {"success": False, "error": "Project has no git repository"},
            status=400,
        )

    # POSTed values may carry JATS markup/entities when they bypass the
    # search-result edge (bulk callers, direct API use); cleaned at save time
    # inside build_bibtex_for_paper.
    paper = {
        "title": request.POST.get("title", ""),
        "authors": request.POST.get("authors", ""),
        "year": request.POST.get("year", ""),
        "journal": request.POST.get("journal", ""),
        "doi": request.POST.get("doi", ""),
        "abstract": request.POST.get("abstract", ""),
        "source": request.POST.get("source", "unknown"),
        "url": request.POST.get("url", ""),
        "pmid": request.POST.get("pmid", ""),
    }
    try:
        citation_key, bibtex_entry = build_bibtex_for_paper(paper)
    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

    try:
        project_path = Path(project.git_clone_path)
        ensure_bibliography_structure(project_path)

        source = paper["source"] or "unknown"
        filename = _write_paper_bib(
            project_path, source, citation_key, bibtex_entry
        )

        logger.info(f"Saved paper to: {project_path / filename}")

        results = regenerate_bibliography(project_path, project.name)
        bib_warning = ""
        if not results.get("success", True):
            bib_warning = "; ".join(results.get("errors", []))[:500]
            logger.warning(f"Bibliography merge failed: {bib_warning}")

        _mirror_to_user_library(
            request.user, project_path, [(paper, citation_key, bibtex_entry)]
        )
        return JsonResponse(
            {
                "success": True,
                "message": f"Saved to {project.name}",
                "project": project.name,
                "citation_key": citation_key,
                "file_path": f"scitex/scholar/bib_files/{filename}",
                "total_citations": results.get("scholar_count", 0),
                "bibliography_warning": bib_warning,
            }
        )

    except Exception as e:
        logger.error(f"Failed to save paper: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def save_papers_bulk(request):
    """Save multiple checked search-result papers to a project bibliography.

    Accepts JSON: {"project_id": <id>, "papers": [{title, authors, year,
    journal, doi, abstract, source, url, pmid}, ...]}.

    Writes one .bib file per valid paper, regenerates the merged
    bibliography once, and reports per-paper skips honestly instead of
    failing the whole batch.
    """
    from apps.infra.project_app.models import Project

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    project_id = payload.get("project_id") or request.POST.get("project_id")
    if not project_id:
        return JsonResponse(
            {
                "success": False,
                "error": "No project selected",
                "saved": 0,
                "skipped": 0,
            },
            status=400,
        )

    papers = payload.get("papers")
    if papers is None:
        papers = []
    if not isinstance(papers, list) or len(papers) == 0:
        return JsonResponse(
            {
                "success": False,
                "error": "No papers selected",
                "saved": 0,
                "skipped": 0,
            },
            status=400,
        )
    if len(papers) > BULK_SAVE_LIMIT:
        return JsonResponse(
            {
                "success": False,
                "error": f"Too many papers (max {BULK_SAVE_LIMIT})",
                "saved": 0,
                "skipped": len(papers),
            },
            status=400,
        )

    project = _resolve_save_project(request.user, project_id)
    if project is None:
        return JsonResponse(
            {
                "success": False,
                "error": "Project not found",
                "saved": 0,
                "skipped": len(papers),
            },
            status=404,
        )

    if not project.git_clone_path:
        return JsonResponse(
            {
                "success": False,
                "error": "Project has no git repository",
                "saved": 0,
                "skipped": len(papers),
            },
            status=400,
        )

    try:
        summary = _save_papers_to_project_path(
            Path(project.git_clone_path), project.name, papers
        )
    except Exception as e:
        logger.error(f"Failed to bulk-save papers: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)

    saved = summary["saved"]
    skipped = summary["skipped"]
    if saved == 0:
        return JsonResponse(
            {
                "success": False,
                "error": "None of the selected papers could be saved",
                **summary,
            },
            status=400,
        )

    message = f"Saved {saved} paper{'s' if saved != 1 else ''} to {project.name}"
    if skipped:
        message += f" ({skipped} skipped)"
    try:
        mirror_items = []
        for paper in papers:
            if not isinstance(paper, dict):
                continue
            try:
                ck, be = build_bibtex_for_paper(paper)
            except ValueError:
                continue
            mirror_items.append((paper, ck, be))
        library_registered = _mirror_to_user_library(
            request.user, Path(project.git_clone_path), mirror_items
        )
    except Exception as e:
        logger.warning(f"User-library mirror skipped: {e}")
        library_registered = 0
    return JsonResponse(
        {
            "success": True,
            "message": message,
            "project": project.name,
            "library_registered": library_registered,
            **summary,
        }
    )


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
