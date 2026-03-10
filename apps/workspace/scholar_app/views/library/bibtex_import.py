#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BibTeX file import endpoint for the scholar library page.

Delegates parsing to scitex.scholar.storage.BibTeXHandler.
Django only manages UserLibrary ORM entries.
"""

from __future__ import annotations

import logging
import os
import tempfile

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ...services.library_cache import LibraryCacheService

logger = logging.getLogger(__name__)


def _paper_obj_to_lib_dict(paper) -> dict:
    """Convert a scitex Paper object to the flat dict expected by LibraryCacheService."""
    m = paper.metadata
    authors = getattr(m.basic, "authors", []) or []
    return {
        "title": getattr(m.basic, "title", "") or "",
        "abstract": getattr(m.basic, "abstract", "") or "",
        "authors": ", ".join(authors) if isinstance(authors, list) else (authors or ""),
        "journal": getattr(m.publication, "journal", "") or "",
        "year": getattr(m.basic, "year", None),
        "doi": getattr(m.id, "doi", "") or "",
        "arxiv_id": getattr(m.id, "arxiv_id", "") or "",
        "pmid": getattr(m.id, "pmid", "") or "",
        "citations": getattr(m.citation_count, "total", None),
        "open_access": getattr(m.access, "is_open_access", False) or False,
        "source": "bibtex_import",
    }


@login_required
@require_http_methods(["POST"])
def api_import_bibtex(request):
    """Import papers from an uploaded BibTeX file into user library.

    POST /api/import/bibtex/
    Form data: bibtex_file (multipart/form-data)

    Returns:
        JSON: {"imported_count": N, "skipped": N}
    """
    tmp_path = None
    try:
        from scitex.scholar.storage import BibTeXHandler

        bibtex_file = request.FILES.get("bibtex_file")
        if not bibtex_file:
            return JsonResponse({"error": "bibtex_file is required"}, status=400)

        with tempfile.NamedTemporaryFile(suffix=".bib", delete=False) as tmp:
            for chunk in bibtex_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        handler = BibTeXHandler()
        papers = handler.papers_from_bibtex(tmp_path)

        if not papers:
            return JsonResponse(
                {
                    "imported_count": 0,
                    "skipped": 0,
                    "message": "No papers found in file",
                }
            )

        imported, skipped = 0, 0
        for paper in papers:
            paper_dict = _paper_obj_to_lib_dict(paper)
            search_index_paper = LibraryCacheService.get_or_create_paper(paper_dict)
            if search_index_paper is None:
                skipped += 1
                continue
            result = LibraryCacheService.add_to_user_library(
                user=request.user,
                paper=search_index_paper,
                reading_status="to_read",
                tags="bibtex",
            )
            if result is not None:
                imported += 1
            else:
                skipped += 1  # already in library

        return JsonResponse({"imported_count": imported, "skipped": skipped})

    except Exception as e:
        logger.error(f"BibTeX library import failed: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# EOF
