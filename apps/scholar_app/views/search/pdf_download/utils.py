#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF download utilities and shared configuration."""

from __future__ import annotations

import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)

# Import scitex.scholar PDF components
try:
    from scitex.scholar.pdf_download import ScholarPDFDownloader
    from scitex.scholar.pdf_download.strategies import try_download_open_access_async

    SCITEX_PDF_AVAILABLE = True
except ImportError:
    SCITEX_PDF_AVAILABLE = False
    ScholarPDFDownloader = None
    try_download_open_access_async = None
    logger.warning("scitex.scholar PDF download not available")


# Common error responses
ERR_SERVICE_UNAVAILABLE = JsonResponse(
    {"status": "error", "error": "PDF download service not available"}, status=503
)
ERR_INVALID_JSON = JsonResponse(
    {"status": "error", "error": "Invalid JSON body"}, status=400
)
ERR_NO_IDENTIFIER = JsonResponse(
    {
        "status": "error",
        "error": "At least one identifier (doi, arxiv_id, pmid, or pdf_url) is required",
    },
    status=400,
)
ERR_NO_IDENTIFIER_SHORT = JsonResponse(
    {
        "status": "error",
        "error": "At least one identifier (doi, arxiv_id, or pmid) is required",
    },
    status=400,
)


def sanitize_filename(title: str, max_length: int = 50) -> str:
    """Sanitize title for use in filename."""
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in title[:max_length])


def generate_pdf_filename(
    title: str, doi: str = "", arxiv_id: str = "", pmid: str = ""
) -> str:
    """Generate a PDF filename from identifiers."""
    safe_title = sanitize_filename(title)
    if doi:
        return f"{safe_title}_{doi.replace('/', '_')}.pdf"
    elif arxiv_id:
        return f"{safe_title}_{arxiv_id.replace('/', '_')}.pdf"
    elif pmid:
        return f"{safe_title}_pmid{pmid}.pdf"
    return f"{safe_title}.pdf"


def get_oa_url_for_identifiers(
    doi: str = "", arxiv_id: str = "", pdf_url: str = ""
) -> tuple[str | None, str | None]:
    """
    Try to find an open access URL for the given identifiers.

    Returns:
        Tuple of (oa_url, oa_method) or (None, None)
    """
    # 1. Direct arXiv
    if arxiv_id:
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf", "arxiv"

    # 2. Provided PDF URL
    if pdf_url:
        return pdf_url, "direct_url"

    # 3. Try to get OA URL from DOI via Unpaywall
    if doi:
        try:
            from scitex.scholar.core import check_oa_status

            oa_result = check_oa_status(doi=doi, use_unpaywall=True)
            if oa_result.is_open_access and oa_result.oa_url:
                logger.info(f"Found OA URL via Unpaywall: {oa_result.oa_url}")
                return oa_result.oa_url, f"unpaywall_{oa_result.status.value}"
        except Exception as e:
            logger.warning(f"Unpaywall lookup failed: {e}")

    return None, None


# EOF
