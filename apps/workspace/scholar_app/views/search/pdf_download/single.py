#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single PDF download endpoint."""

from __future__ import annotations

import asyncio
import json
import logging
import traceback
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ....integrations.scitex_scholar import get_user_scitex_dir
from .utils import (
    ERR_INVALID_JSON,
    ERR_NO_IDENTIFIER,
    ERR_SERVICE_UNAVAILABLE,
    SCITEX_PDF_AVAILABLE,
    generate_pdf_filename,
    get_oa_url_for_identifiers,
    try_download_open_access_async,
)

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def api_download_pdf(request):
    """
    Download PDF for a paper.

    Request body (JSON):
        - doi: DOI of the paper (optional)
        - arxiv_id: arXiv ID (optional)
        - pmid: PubMed ID (optional)
        - pdf_url: Direct PDF URL (optional)
        - title: Paper title for filename (optional)
        - prefer_open_access: Prefer open access sources (default: true)

    Returns:
        JSON response with download status and file path
    """
    if not SCITEX_PDF_AVAILABLE:
        return ERR_SERVICE_UNAVAILABLE

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return ERR_INVALID_JSON

    doi = data.get("doi", "").strip()
    arxiv_id = data.get("arxiv_id", "").strip()
    pmid = data.get("pmid", "").strip()
    pdf_url = data.get("pdf_url", "").strip()
    title = data.get("title", "paper").strip()

    if not any([doi, arxiv_id, pmid, pdf_url]):
        return ERR_NO_IDENTIFIER

    # Get user-specific paths
    session_key = request.session.session_key
    user = request.user if request.user.is_authenticated else None
    user_scitex_dir = get_user_scitex_dir(user, session_key=session_key)

    # Create download directory
    downloads_dir = user_scitex_dir / "scholar" / "library" / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    filename = generate_pdf_filename(title, doi, arxiv_id, pmid)
    output_path = downloads_dir / filename

    # Build paper metadata for downloader
    paper_meta = {"doi": doi, "arxiv_id": arxiv_id, "pmid": pmid, "title": title}

    # Get OA URL
    oa_url, oa_method = get_oa_url_for_identifiers(doi, arxiv_id, pdf_url)

    if not oa_url:
        return JsonResponse(
            {
                "status": "success",
                "downloaded": False,
                "reason": "No open access URL available. Browser-based download not supported in web interface.",
            }
        )

    async def download_async():
        result = await try_download_open_access_async(
            oa_url=oa_url, output_path=output_path, metadata=paper_meta, timeout=60
        )
        if result:
            return str(result), oa_method or "open_access"
        return None, None

    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        downloaded_path, method = loop.run_until_complete(download_async())

        if downloaded_path and Path(downloaded_path).exists():
            relative_path = Path(downloaded_path).relative_to(user_scitex_dir)
            return JsonResponse(
                {
                    "status": "success",
                    "downloaded": True,
                    "path": str(relative_path),
                    "filename": filename,
                    "method": method,
                    "size_bytes": Path(downloaded_path).stat().st_size,
                }
            )
        else:
            return JsonResponse(
                {
                    "status": "success",
                    "downloaded": False,
                    "reason": "PDF not available from open access sources",
                }
            )

    except Exception as e:
        logger.error(f"PDF download failed: {e}\n{traceback.format_exc()}")
        return JsonResponse(
            {
                "status": "error",
                "error": str(e),
                "detail": traceback.format_exc() if settings.DEBUG else None,
            },
            status=500,
        )


# EOF
