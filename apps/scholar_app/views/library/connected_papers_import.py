#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Connected Papers import/export endpoints for the scholar library page.

Import: delegates to scitex.scholar.migration.from_connected_papers.
Export: delegates to scitex.scholar.migration.to_connected_papers.
Django only manages ORM entries and file responses.
"""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ...services.library_cache import LibraryCacheService

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def connected_papers_import(request):
    """Import papers from a Connected Papers graph into user library.

    POST body (JSON):
        paper_id: str          Semantic Scholar paper ID (40-char SHA)
        output_format: str     "papers" (default) or "citation_graph"
        dry_run: bool          If True, return stats only
        cp_api_key: str|null   Connected Papers API key (optional)
        s2_api_key: str|null   Semantic Scholar API key (optional)
    """
    try:
        from scitex.scholar.migration import from_connected_papers

        data = json.loads(request.body)
        paper_id = data.get("paper_id", "").strip()

        if not paper_id:
            return JsonResponse({"error": "paper_id is required"}, status=400)

        result = from_connected_papers(
            paper_id,
            cp_api_key=data.get("cp_api_key"),
            s2_api_key=data.get("s2_api_key"),
            output_format=data.get("output_format", "papers"),
            dry_run=data.get("dry_run", False),
        )

        if not result.get("success"):
            return JsonResponse(
                {"error": result.get("error", "Unknown error")}, status=400
            )

        if data.get("dry_run"):
            return JsonResponse(result)

        # Import papers into library
        papers = result.get("papers")
        if papers is None:
            return JsonResponse(result)

        imported, skipped = 0, 0
        for paper in papers:
            paper_dict = _paper_to_dict(paper)
            search_index_paper = LibraryCacheService.get_or_create_paper(paper_dict)
            if search_index_paper is None:
                skipped += 1
                continue
            lib_entry = LibraryCacheService.add_to_user_library(
                user=request.user,
                paper=search_index_paper,
                collection_name="Connected Papers",
                reading_status="to_read",
                tags="connected-papers",
            )
            if lib_entry is not None:
                imported += 1
            else:
                skipped += 1

        result["imported"] = imported
        result["skipped"] = skipped
        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    except Exception as e:
        logger.error(f"Connected Papers import failed: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def connected_papers_status(request):
    """Check if Connected Papers integration is available."""
    try:
        import connectedpapers  # noqa: F401

        return JsonResponse({"available": True})
    except ImportError:
        return JsonResponse(
            {
                "available": False,
                "error": "connectedpapers-py not installed",
            }
        )


def _paper_to_dict(paper) -> dict:
    """Convert a scitex Paper object to flat dict for LibraryCacheService."""
    m = paper.metadata
    authors = m.basic.authors or []
    return {
        "title": m.basic.title or "",
        "abstract": m.basic.abstract or "",
        "authors": ", ".join(authors) if isinstance(authors, list) else (authors or ""),
        "journal": m.publication.journal or "",
        "year": m.basic.year,
        "doi": m.id.doi or "",
        "arxiv_id": m.id.arxiv_id or "",
        "pmid": m.id.pmid or "",
        "citations": m.citation_count.total,
        "open_access": m.access.is_open_access or False,
        "source": "connected_papers",
    }


# EOF
