#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zotero import endpoints for the scholar library page.

All scitex.scholar logic delegates to ZoteroLocalReader.
Django only manages UserLibrary ORM entries.
"""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ...services.library_cache import LibraryCacheService

logger = logging.getLogger(__name__)


def _paper_to_dict(paper) -> dict:
    """Convert a scitex Paper object to the flat dict format expected by LibraryCacheService."""
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
        "source": "zotero",
    }


@login_required
@require_http_methods(["GET"])
def zotero_status(request):
    """Check if local Zotero database is accessible."""
    try:
        from scitex.scholar.integration.zotero import ZoteroLocalReader

        reader = ZoteroLocalReader()
        return JsonResponse({"available": True, "db_path": str(reader.db_path)})
    except FileNotFoundError:
        return JsonResponse({"available": False, "db_path": None})
    except Exception as e:
        logger.warning(f"Zotero status check failed: {e}")
        return JsonResponse({"available": False, "db_path": None, "error": str(e)})


@login_required
@require_http_methods(["POST"])
def zotero_import(request):
    """Import papers from local Zotero database into user library.

    POST body (JSON):
        mode: "all" | "tags" | "collection"
        tags: list[str]        (for mode="tags")
        collection: str        (for mode="collection")
        match_all: bool        (for mode="tags", default False)
        db_path: str | null    (optional override; null = auto-detect)
    """
    try:
        from scitex.scholar.integration.zotero import ZoteroLocalReader

        data = json.loads(request.body)
        mode = data.get("mode", "all")
        db_path = data.get("db_path") or None

        reader = ZoteroLocalReader(db_path=db_path)

        if mode == "tags":
            tags = data.get("tags", [])
            papers = reader.read_by_tags(tags, match_all=data.get("match_all", False))
        elif mode == "collection":
            papers = reader.read_by_collection(data.get("collection", ""))
        else:
            papers = reader.read_all()

        imported, skipped = 0, 0
        for paper in papers:
            paper_dict = _paper_to_dict(paper)
            search_index_paper = LibraryCacheService.get_or_create_paper(paper_dict)
            if search_index_paper is None:
                skipped += 1
                continue
            result = LibraryCacheService.add_to_user_library(
                user=request.user,
                paper=search_index_paper,
                collection_name="Zotero",
                reading_status="to_read",
                tags="zotero",
            )
            if result is not None:
                imported += 1
            else:
                skipped += 1  # already in library

        return JsonResponse(
            {"imported": imported, "skipped": skipped, "total": len(papers)}
        )

    except FileNotFoundError as e:
        return JsonResponse({"error": str(e)}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    except Exception as e:
        logger.error(f"Zotero import failed: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def zotero_collections(request):
    """List available Zotero collections from local database."""
    try:
        from scitex.scholar.integration.zotero import ZoteroLocalReader

        reader = ZoteroLocalReader()
        return JsonResponse({"collections": reader.list_collections()})
    except FileNotFoundError as e:
        return JsonResponse({"error": str(e)}, status=404)
    except Exception as e:
        logger.error(f"Failed to list Zotero collections: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def zotero_tags(request):
    """List available Zotero tags from local database with counts."""
    try:
        from scitex.scholar.integration.zotero import ZoteroLocalReader

        reader = ZoteroLocalReader()
        return JsonResponse({"tags": reader.list_tags()})
    except FileNotFoundError as e:
        return JsonResponse({"error": str(e)}, status=404)
    except Exception as e:
        logger.error(f"Failed to list Zotero tags: {e}")
        return JsonResponse({"error": str(e)}, status=500)


# EOF
