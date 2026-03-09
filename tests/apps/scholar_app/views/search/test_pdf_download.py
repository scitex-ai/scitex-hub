#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/scholar_app/views/search/pdf_download.py"""

import pytest

# from apps.workspace.scholar_app.views.search.pdf_download import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/scholar_app/views/search/pdf_download.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/search/pdf_download.py
# """
# PDF Download API endpoints for Scholar Search.
#
# Provides server-side PDF download functionality using scitex.scholar's
# PDF downloader with stealth mode support.
# """
#
# from __future__ import annotations
# import os
# import asyncio
# import logging
# from pathlib import Path
# from typing import Optional
#
# from django.http import JsonResponse, FileResponse
# from django.views.decorators.http import require_http_methods
# from django.views.decorators.csrf import csrf_exempt
# from django.conf import settings
#
# from ...integrations.scitex_scholar import get_user_scitex_dir, get_scholar_config
#
# logger = logging.getLogger(__name__)
#
# # Import scitex.scholar PDF components
# try:
#     from scitex.scholar.pdf_download import ScholarPDFDownloader
#     from scitex.scholar.pdf_download.strategies import try_download_open_access_async
#     SCITEX_PDF_AVAILABLE = True
# except ImportError:
#     SCITEX_PDF_AVAILABLE = False
#     logger.warning("scitex.scholar PDF download not available")
#
#
# @require_http_methods(["POST"])
# def api_download_pdf(request):
#     """
#     Download PDF for a paper.
#
#     Request body (JSON):
#         - doi: DOI of the paper (optional)
#         - arxiv_id: arXiv ID (optional)
#         - pmid: PubMed ID (optional)
#         - pdf_url: Direct PDF URL (optional)
#         - title: Paper title for filename (optional)
#         - prefer_open_access: Prefer open access sources (default: true)
#
#     Returns:
#         JSON response with download status and file path
#     """
#     import json
#
#     if not SCITEX_PDF_AVAILABLE:
#         return JsonResponse({
#             "status": "error",
#             "error": "PDF download service not available",
#         }, status=503)
#
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({
#             "status": "error",
#             "error": "Invalid JSON body",
#         }, status=400)
#
#     doi = data.get("doi", "").strip()
#     arxiv_id = data.get("arxiv_id", "").strip()
#     pmid = data.get("pmid", "").strip()
#     pdf_url = data.get("pdf_url", "").strip()
#     title = data.get("title", "paper").strip()
#     prefer_open_access = data.get("prefer_open_access", True)
#
#     if not any([doi, arxiv_id, pmid, pdf_url]):
#         return JsonResponse({
#             "status": "error",
#             "error": "At least one identifier (doi, arxiv_id, pmid, or pdf_url) is required",
#         }, status=400)
#
#     # Get user-specific paths
#     session_key = request.session.session_key
#     user = request.user if request.user.is_authenticated else None
#     user_scitex_dir = get_user_scitex_dir(user, session_key=session_key)
#     config = get_scholar_config(user)
#
#     # Create download directory
#     downloads_dir = user_scitex_dir / "scholar" / "library" / "downloads"
#     downloads_dir.mkdir(parents=True, exist_ok=True)
#
#     # Generate filename
#     safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title[:50])
#     if doi:
#         filename = f"{safe_title}_{doi.replace('/', '_')}.pdf"
#     elif arxiv_id:
#         filename = f"{safe_title}_{arxiv_id.replace('/', '_')}.pdf"
#     elif pmid:
#         filename = f"{safe_title}_pmid{pmid}.pdf"
#     else:
#         filename = f"{safe_title}.pdf"
#
#     output_path = downloads_dir / filename
#
#     # Build paper metadata for downloader
#     paper_meta = {
#         "doi": doi,
#         "arxiv_id": arxiv_id,
#         "pmid": pmid,
#         "title": title,
#     }
#
#     # Construct OA URL - try multiple methods
#     oa_url = None
#     oa_method = None
#
#     # 1. Direct arXiv
#     if arxiv_id:
#         oa_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
#         oa_method = "arxiv"
#
#     # 2. Provided PDF URL
#     elif pdf_url:
#         oa_url = pdf_url
#         oa_method = "direct_url"
#
#     # 3. Try to get OA URL from DOI via Unpaywall
#     elif doi:
#         try:
#             from scitex.scholar.core import check_oa_status
#             oa_result = check_oa_status(doi=doi, use_unpaywall=True)
#             if oa_result.is_open_access and oa_result.oa_url:
#                 oa_url = oa_result.oa_url
#                 oa_method = f"unpaywall_{oa_result.status.value}"
#                 logger.info(f"Found OA URL via Unpaywall: {oa_url}")
#         except Exception as e:
#             logger.warning(f"Unpaywall lookup failed: {e}")
#
#     # If no OA URL found, we can't download without browser
#     if not oa_url:
#         return JsonResponse({
#             "status": "success",
#             "downloaded": False,
#             "reason": "No open access URL available. Browser-based download not supported in web interface.",
#         })
#
#     async def download_async():
#         # Try open access download
#         result = await try_download_open_access_async(
#             oa_url=oa_url,
#             output_path=output_path,
#             metadata=paper_meta,
#             timeout=60,
#         )
#         if result:
#             return str(result), oa_method or "open_access"
#         return None, None
#
#     try:
#         # Use get_event_loop for Django compatibility (asyncio.run can conflict with existing loops)
#         try:
#             loop = asyncio.get_event_loop()
#         except RuntimeError:
#             loop = asyncio.new_event_loop()
#             asyncio.set_event_loop(loop)
#
#         downloaded_path, method = loop.run_until_complete(download_async())
#
#         if downloaded_path and Path(downloaded_path).exists():
#             # Return relative path for serving
#             relative_path = Path(downloaded_path).relative_to(user_scitex_dir)
#             return JsonResponse({
#                 "status": "success",
#                 "downloaded": True,
#                 "path": str(relative_path),
#                 "filename": filename,
#                 "method": method,
#                 "size_bytes": Path(downloaded_path).stat().st_size,
#             })
#         else:
#             return JsonResponse({
#                 "status": "success",
#                 "downloaded": False,
#                 "reason": "PDF not available from open access sources",
#             })
#
#     except Exception as e:
#         import traceback
#         logger.error(f"PDF download failed: {e}\n{traceback.format_exc()}")
#         return JsonResponse({
#             "status": "error",
#             "error": str(e),
#             "detail": traceback.format_exc() if settings.DEBUG else None,
#         }, status=500)
#
#
# @require_http_methods(["GET"])
# def api_check_pdf_status(request):
#     """
#     Check if PDF exists for given identifiers.
#
#     Query parameters:
#         - doi: DOI of the paper
#         - arxiv_id: arXiv ID
#         - pmid: PubMed ID
#
#     Returns:
#         JSON with PDF availability status
#     """
#     doi = request.GET.get("doi", "").strip()
#     arxiv_id = request.GET.get("arxiv_id", "").strip()
#     pmid = request.GET.get("pmid", "").strip()
#
#     if not any([doi, arxiv_id, pmid]):
#         return JsonResponse({
#             "status": "error",
#             "error": "At least one identifier (doi, arxiv_id, or pmid) is required",
#         }, status=400)
#
#     # Get user-specific paths
#     session_key = request.session.session_key
#     user = request.user if request.user.is_authenticated else None
#     user_scitex_dir = get_user_scitex_dir(user, session_key=session_key)
#
#     downloads_dir = user_scitex_dir / "scholar" / "library" / "downloads"
#     master_dir = user_scitex_dir / "scholar" / "library" / "MASTER"
#
#     # Check for existing PDF
#     patterns = []
#     if doi:
#         patterns.append(f"*{doi.replace('/', '_')}*.pdf")
#     if arxiv_id:
#         patterns.append(f"*{arxiv_id.replace('/', '_')}*.pdf")
#     if pmid:
#         patterns.append(f"*pmid{pmid}*.pdf")
#
#     found_path = None
#     for search_dir in [downloads_dir, master_dir]:
#         if not search_dir.exists():
#             continue
#         for pattern in patterns:
#             matches = list(search_dir.glob(pattern))
#             if matches:
#                 found_path = matches[0]
#                 break
#         if found_path:
#             break
#
#     if found_path and found_path.exists():
#         relative_path = found_path.relative_to(user_scitex_dir)
#         return JsonResponse({
#             "status": "success",
#             "has_pdf": True,
#             "path": str(relative_path),
#             "filename": found_path.name,
#             "size_bytes": found_path.stat().st_size,
#         })
#     else:
#         # Use scitex OA detection for comprehensive check
#         try:
#             from scitex.scholar.core import detect_oa_from_identifiers
#             oa_result = detect_oa_from_identifiers(
#                 doi=doi,
#                 arxiv_id=arxiv_id,
#                 pmcid=None,  # pmid != pmcid
#             )
#             is_open_access = oa_result.is_open_access
#             can_download = oa_result.confidence >= 0.8 and is_open_access
#             oa_url = oa_result.oa_url
#         except ImportError:
#             # Fallback: only arXiv is guaranteed open access
#             is_open_access = bool(arxiv_id)
#             can_download = is_open_access
#             oa_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None
#
#         return JsonResponse({
#             "status": "success",
#             "has_pdf": False,
#             "is_open_access": is_open_access,
#             "can_download": can_download,
#             "oa_url": oa_url,
#         })
#
#
# @require_http_methods(["POST"])
# def api_download_pdf_bulk(request):
#     """
#     Queue bulk PDF downloads for multiple papers.
#
#     Request body (JSON):
#         - papers: List of paper objects with doi/arxiv_id/pmid
#         - prefer_open_access: Prefer open access sources (default: true)
#
#     Returns:
#         JSON with download task ID and initial status
#     """
#     import json
#
#     if not SCITEX_PDF_AVAILABLE:
#         return JsonResponse({
#             "status": "error",
#             "error": "PDF download service not available",
#         }, status=503)
#
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({
#             "status": "error",
#             "error": "Invalid JSON body",
#         }, status=400)
#
#     papers = data.get("papers", [])
#     if not papers:
#         return JsonResponse({
#             "status": "error",
#             "error": "No papers provided",
#         }, status=400)
#
#     if len(papers) > 50:
#         return JsonResponse({
#             "status": "error",
#             "error": "Maximum 50 papers per bulk download",
#         }, status=400)
#
#     # Get user-specific paths
#     session_key = request.session.session_key
#     user = request.user if request.user.is_authenticated else None
#     user_scitex_dir = get_user_scitex_dir(user, session_key=session_key)
#
#     downloads_dir = user_scitex_dir / "scholar" / "library" / "downloads"
#     downloads_dir.mkdir(parents=True, exist_ok=True)
#
#     # Process papers synchronously for now
#     # TODO: Use Celery for async background processing
#     results = []
#     for paper in papers:
#         doi = paper.get("doi", "").strip()
#         arxiv_id = paper.get("arxiv_id", "").strip()
#         pmid = paper.get("pmid", "").strip()
#         title = paper.get("title", "paper").strip()
#
#         identifier = doi or arxiv_id or pmid
#         if not identifier:
#             results.append({
#                 "identifier": None,
#                 "status": "skipped",
#                 "reason": "No identifier",
#             })
#             continue
#
#         # Check if already downloaded
#         patterns = []
#         if doi:
#             patterns.append(f"*{doi.replace('/', '_')}*.pdf")
#         if arxiv_id:
#             patterns.append(f"*{arxiv_id.replace('/', '_')}*.pdf")
#
#         already_exists = False
#         for pattern in patterns:
#             if list(downloads_dir.glob(pattern)):
#                 already_exists = True
#                 break
#
#         if already_exists:
#             results.append({
#                 "identifier": identifier,
#                 "status": "exists",
#                 "title": title,
#             })
#             continue
#
#         # Only attempt open access downloads for safety
#         if arxiv_id:
#             oa_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
#             safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title[:50])
#             filename = f"{safe_title}_{arxiv_id.replace('/', '_')}.pdf"
#             output_path = downloads_dir / filename
#
#             try:
#                 downloaded_path = asyncio.run(
#                     try_download_open_access_async(
#                         oa_url=oa_url,
#                         output_path=output_path,
#                         metadata=paper,
#                         timeout=30,
#                     )
#                 )
#                 if downloaded_path:
#                     results.append({
#                         "identifier": identifier,
#                         "status": "downloaded",
#                         "title": title,
#                         "filename": filename,
#                     })
#                 else:
#                     results.append({
#                         "identifier": identifier,
#                         "status": "failed",
#                         "title": title,
#                         "reason": "Download failed",
#                     })
#             except Exception as e:
#                 results.append({
#                     "identifier": identifier,
#                     "status": "error",
#                     "title": title,
#                     "reason": str(e),
#                 })
#         else:
#             results.append({
#                 "identifier": identifier,
#                 "status": "skipped",
#                 "title": title,
#                 "reason": "Only open access downloads supported in bulk mode",
#             })
#
#     # Summary
#     downloaded = sum(1 for r in results if r["status"] == "downloaded")
#     existed = sum(1 for r in results if r["status"] == "exists")
#     failed = sum(1 for r in results if r["status"] in ["failed", "error"])
#     skipped = sum(1 for r in results if r["status"] == "skipped")
#
#     return JsonResponse({
#         "status": "success",
#         "summary": {
#             "total": len(papers),
#             "downloaded": downloaded,
#             "existed": existed,
#             "failed": failed,
#             "skipped": skipped,
#         },
#         "results": results,
#     })
#
#
# @require_http_methods(["GET"])
# def api_serve_pdf(request):
#     """
#     Serve a downloaded PDF file.
#
#     Query parameters:
#         - path: Relative path to PDF within user's scitex directory
#
#     Returns:
#         PDF file response or error
#     """
#     relative_path = request.GET.get("path", "").strip()
#     if not relative_path:
#         return JsonResponse({
#             "status": "error",
#             "error": "Path parameter required",
#         }, status=400)
#
#     # Security: prevent directory traversal
#     if ".." in relative_path or relative_path.startswith("/"):
#         return JsonResponse({
#             "status": "error",
#             "error": "Invalid path",
#         }, status=400)
#
#     # Get user-specific paths
#     session_key = request.session.session_key
#     user = request.user if request.user.is_authenticated else None
#     user_scitex_dir = get_user_scitex_dir(user, session_key=session_key)
#
#     full_path = user_scitex_dir / relative_path
#     if not full_path.exists() or not full_path.is_file():
#         return JsonResponse({
#             "status": "error",
#             "error": "File not found",
#         }, status=404)
#
#     # Ensure file is within user's directory
#     try:
#         full_path.resolve().relative_to(user_scitex_dir.resolve())
#     except ValueError:
#         return JsonResponse({
#             "status": "error",
#             "error": "Access denied",
#         }, status=403)
#
#     return FileResponse(
#         open(full_path, "rb"),
#         content_type="application/pdf",
#         filename=full_path.name,
#     )
#
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/scholar_app/views/search/pdf_download.py
# --------------------------------------------------------------------------------
