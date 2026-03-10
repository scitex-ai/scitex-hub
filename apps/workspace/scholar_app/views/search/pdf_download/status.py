#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF status check and file serving endpoints."""

from __future__ import annotations

import logging

from django.http import FileResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from ....integrations.scitex_scholar import get_user_scitex_dir
from .utils import ERR_NO_IDENTIFIER_SHORT

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def api_check_pdf_status(request):
    """
    Check if PDF exists for given identifiers.

    Query parameters:
        - doi: DOI of the paper
        - arxiv_id: arXiv ID
        - pmid: PubMed ID

    Returns:
        JSON with PDF availability status
    """
    doi = request.GET.get("doi", "").strip()
    arxiv_id = request.GET.get("arxiv_id", "").strip()
    pmid = request.GET.get("pmid", "").strip()

    if not any([doi, arxiv_id, pmid]):
        return ERR_NO_IDENTIFIER_SHORT

    # Get user-specific paths
    session_key = request.session.session_key
    user = request.user if request.user.is_authenticated else None
    user_scitex_dir = get_user_scitex_dir(user, session_key=session_key)

    downloads_dir = user_scitex_dir / "scholar" / "library" / "downloads"
    master_dir = user_scitex_dir / "scholar" / "library" / "MASTER"

    # Check for existing PDF
    found_path = _find_existing_pdf(downloads_dir, master_dir, doi, arxiv_id, pmid)

    if found_path and found_path.exists():
        relative_path = found_path.relative_to(user_scitex_dir)
        return JsonResponse(
            {
                "status": "success",
                "has_pdf": True,
                "path": str(relative_path),
                "filename": found_path.name,
                "size_bytes": found_path.stat().st_size,
            }
        )

    # Check OA availability
    oa_info = _check_oa_availability(doi, arxiv_id)
    return JsonResponse({"status": "success", "has_pdf": False, **oa_info})


def _find_existing_pdf(downloads_dir, master_dir, doi: str, arxiv_id: str, pmid: str):
    """Find existing PDF in user directories."""
    patterns = []
    if doi:
        patterns.append(f"*{doi.replace('/', '_')}*.pdf")
    if arxiv_id:
        patterns.append(f"*{arxiv_id.replace('/', '_')}*.pdf")
    if pmid:
        patterns.append(f"*pmid{pmid}*.pdf")

    for search_dir in [downloads_dir, master_dir]:
        if not search_dir.exists():
            continue
        for pattern in patterns:
            matches = list(search_dir.glob(pattern))
            if matches:
                return matches[0]
    return None


def _check_oa_availability(doi: str, arxiv_id: str) -> dict:
    """Check open access availability using scitex."""
    try:
        from scitex.scholar.core import detect_oa_from_identifiers

        oa_result = detect_oa_from_identifiers(doi=doi, arxiv_id=arxiv_id, pmcid=None)
        return {
            "is_open_access": oa_result.is_open_access,
            "can_download": oa_result.confidence >= 0.8 and oa_result.is_open_access,
            "oa_url": oa_result.oa_url,
        }
    except ImportError:
        # Fallback: only arXiv is guaranteed open access
        is_open_access = bool(arxiv_id)
        return {
            "is_open_access": is_open_access,
            "can_download": is_open_access,
            "oa_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None,
        }


@require_http_methods(["GET"])
def api_serve_pdf(request):
    """
    Serve a downloaded PDF file.

    Query parameters:
        - path: Relative path to PDF within user's scitex directory

    Returns:
        PDF file response or error
    """
    relative_path = request.GET.get("path", "").strip()
    if not relative_path:
        return JsonResponse(
            {"status": "error", "error": "Path parameter required"}, status=400
        )

    # Security: prevent directory traversal
    if ".." in relative_path or relative_path.startswith("/"):
        return JsonResponse({"status": "error", "error": "Invalid path"}, status=400)

    # Get user-specific paths
    session_key = request.session.session_key
    user = request.user if request.user.is_authenticated else None
    user_scitex_dir = get_user_scitex_dir(user, session_key=session_key)

    full_path = user_scitex_dir / relative_path
    if not full_path.exists() or not full_path.is_file():
        return JsonResponse({"status": "error", "error": "File not found"}, status=404)

    # Ensure file is within user's directory
    try:
        full_path.resolve().relative_to(user_scitex_dir.resolve())
    except ValueError:
        return JsonResponse({"status": "error", "error": "Access denied"}, status=403)

    return FileResponse(
        open(full_path, "rb"), content_type="application/pdf", filename=full_path.name
    )


# EOF
