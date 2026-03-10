#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bulk PDF download endpoint."""

from __future__ import annotations

import asyncio
import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ....integrations.scitex_scholar import get_user_scitex_dir
from .utils import (
    ERR_INVALID_JSON,
    ERR_SERVICE_UNAVAILABLE,
    SCITEX_PDF_AVAILABLE,
    sanitize_filename,
    try_download_open_access_async,
)

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def api_download_pdf_bulk(request):
    """
    Queue bulk PDF downloads for multiple papers.

    Request body (JSON):
        - papers: List of paper objects with doi/arxiv_id/pmid
        - prefer_open_access: Prefer open access sources (default: true)

    Returns:
        JSON with download task ID and initial status
    """
    if not SCITEX_PDF_AVAILABLE:
        return ERR_SERVICE_UNAVAILABLE

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return ERR_INVALID_JSON

    papers = data.get("papers", [])
    if not papers:
        return JsonResponse(
            {"status": "error", "error": "No papers provided"}, status=400
        )

    if len(papers) > 50:
        return JsonResponse(
            {"status": "error", "error": "Maximum 50 papers per bulk download"},
            status=400,
        )

    # Get user-specific paths
    session_key = request.session.session_key
    user = request.user if request.user.is_authenticated else None
    user_scitex_dir = get_user_scitex_dir(user, session_key=session_key)

    downloads_dir = user_scitex_dir / "scholar" / "library" / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    results = _process_bulk_papers(papers, downloads_dir)

    # Summary
    downloaded = sum(1 for r in results if r["status"] == "downloaded")
    existed = sum(1 for r in results if r["status"] == "exists")
    failed = sum(1 for r in results if r["status"] in ["failed", "error"])
    skipped = sum(1 for r in results if r["status"] == "skipped")

    return JsonResponse(
        {
            "status": "success",
            "summary": {
                "total": len(papers),
                "downloaded": downloaded,
                "existed": existed,
                "failed": failed,
                "skipped": skipped,
            },
            "results": results,
        }
    )


def _process_bulk_papers(papers: list, downloads_dir) -> list:
    """Process multiple papers for bulk download."""
    results = []
    for paper in papers:
        result = _process_single_paper(paper, downloads_dir)
        results.append(result)
    return results


def _process_single_paper(paper: dict, downloads_dir) -> dict:
    """Process a single paper for bulk download."""
    doi = paper.get("doi", "").strip()
    arxiv_id = paper.get("arxiv_id", "").strip()
    pmid = paper.get("pmid", "").strip()
    title = paper.get("title", "paper").strip()

    identifier = doi or arxiv_id or pmid
    if not identifier:
        return {"identifier": None, "status": "skipped", "reason": "No identifier"}

    # Check if already downloaded
    if _check_existing_pdf(downloads_dir, doi, arxiv_id):
        return {"identifier": identifier, "status": "exists", "title": title}

    # Only attempt open access downloads for arXiv
    if not arxiv_id:
        return {
            "identifier": identifier,
            "status": "skipped",
            "title": title,
            "reason": "Only open access downloads supported in bulk mode",
        }

    return _download_arxiv_pdf(arxiv_id, title, paper, downloads_dir)


def _check_existing_pdf(downloads_dir, doi: str, arxiv_id: str) -> bool:
    """Check if PDF already exists in downloads directory."""
    patterns = []
    if doi:
        patterns.append(f"*{doi.replace('/', '_')}*.pdf")
    if arxiv_id:
        patterns.append(f"*{arxiv_id.replace('/', '_')}*.pdf")

    for pattern in patterns:
        if list(downloads_dir.glob(pattern)):
            return True
    return False


def _download_arxiv_pdf(arxiv_id: str, title: str, paper: dict, downloads_dir) -> dict:
    """Download PDF from arXiv."""
    oa_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    safe_title = sanitize_filename(title)
    filename = f"{safe_title}_{arxiv_id.replace('/', '_')}.pdf"
    output_path = downloads_dir / filename

    try:
        downloaded_path = asyncio.run(
            try_download_open_access_async(
                oa_url=oa_url, output_path=output_path, metadata=paper, timeout=30
            )
        )
        if downloaded_path:
            return {
                "identifier": arxiv_id,
                "status": "downloaded",
                "title": title,
                "filename": filename,
            }
        return {
            "identifier": arxiv_id,
            "status": "failed",
            "title": title,
            "reason": "Download failed",
        }
    except Exception as e:
        return {
            "identifier": arxiv_id,
            "status": "error",
            "title": title,
            "reason": str(e),
        }


# EOF
