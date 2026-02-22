#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Library views for Scholar App

This module handles personal library and collection management views.
"""

import json
import logging
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from ...models import Collection, UserLibrary
from ...models import SearchIndex as Paper

logger = logging.getLogger(__name__)


@login_required
def personal_library(request):
    """Display user's personal library of papers"""
    user = request.user
    papers = UserLibrary.objects.filter(user=user).select_related("paper")
    collections = Collection.objects.filter(user=user)

    context = {
        "papers": papers,
        "collections": collections,
        "page_title": "Personal Library",
    }

    return render(request, "scholar_app/personal_library.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def api_library_papers(request):
    """API endpoint for library papers management"""
    if request.method == "GET":
        # Get user's library papers with full metadata
        try:
            entries = (
                UserLibrary.objects.filter(user=request.user)
                .select_related("paper", "paper__journal")
                .prefetch_related("collections", "paper__authors")
                .order_by("-saved_at")
            )
            papers = []
            for entry in entries:
                p = entry.paper
                collection_ids = [str(c.id) for c in entry.collections.all()]
                papers.append(
                    {
                        "id": str(entry.id),
                        "paper_id": str(p.id) if p else None,
                        "title": p.title if p else "Unknown",
                        "doi": p.doi if p else None,
                        "journal": str(p.journal) if p and p.journal else None,
                        "year": (
                            p.publication_date.year
                            if p and p.publication_date
                            else None
                        ),
                        "authors": (
                            ", ".join(
                                f"{a.first_name} {a.last_name}" for a in p.authors.all()
                            )
                            if p
                            else None
                        ),
                        "abstract": (
                            p.abstract if p and hasattr(p, "abstract") else None
                        ),
                        "reading_status": entry.reading_status,
                        "importance_rating": entry.importance_rating,
                        "personal_notes": entry.personal_notes,
                        "tags": entry.get_tags_list(),
                        "saved_at": (
                            entry.saved_at.isoformat() if entry.saved_at else None
                        ),
                        "pdf_path": entry.user_library_pdf_path or None,
                        "collection_ids": collection_ids,
                    }
                )

            # Also return summary stats
            from django.db.models import Count

            stats = (
                UserLibrary.objects.filter(user=request.user)
                .values("reading_status")
                .annotate(count=Count("id"))
            )
            status_counts = {s["reading_status"]: s["count"] for s in stats}

            return JsonResponse(
                {
                    "success": True,
                    "papers": papers,
                    "total": len(papers),
                    "stats": status_counts,
                }
            )
        except Exception as e:
            logger.error(f"Error fetching library papers: {e}")
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    elif request.method == "POST":
        # Add paper to library
        try:
            data = json.loads(request.body)
            paper_id = data.get("paper_id")

            if not paper_id:
                return JsonResponse(
                    {"success": False, "error": "paper_id is required"}, status=400
                )

            paper = Paper.objects.get(id=paper_id)
            lib_entry, created = UserLibrary.objects.get_or_create(
                user=request.user, paper=paper
            )

            if created:
                messages.success(request, f"Paper '{paper.title}' added to library")

            return JsonResponse(
                {"success": True, "created": created, "paper_id": str(paper.id)}
            )

        except Paper.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Paper not found"}, status=404
            )
        except Exception as e:
            logger.error(f"Error adding paper to library: {e}")
            return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_library_collections(request):
    """API endpoint for user's collections"""
    try:
        from django.db.models import Count

        collections = (
            Collection.objects.filter(user=request.user)
            .annotate(paper_count=Count("library_papers"))
            .values("id", "name", "description", "color", "icon", "paper_count")
        )

        return JsonResponse({"success": True, "collections": list(collections)})
    except Exception as e:
        logger.error(f"Error fetching collections: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def api_create_collection(request):
    """API endpoint to create a new collection"""
    try:
        data = json.loads(request.body)
        name = data.get("name")
        description = data.get("description", "")

        if not name:
            return JsonResponse(
                {"success": False, "error": "Collection name is required"}, status=400
            )

        collection = Collection.objects.create(
            user=request.user, name=name, description=description
        )

        return JsonResponse(
            {
                "success": True,
                "collection_id": str(collection.id),
                "name": collection.name,
            }
        )
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def api_update_library_paper(request, paper_id):
    """API endpoint to update paper in library"""
    try:
        paper_id = UUID(str(paper_id))
        data = json.loads(request.body)

        lib_entry = UserLibrary.objects.get(user=request.user, paper_id=paper_id)

        # Update fields as needed
        if "personal_notes" in data:
            lib_entry.personal_notes = data["personal_notes"]
        if "notes" in data:
            lib_entry.personal_notes = data["notes"]
        if "tags" in data:
            lib_entry.tags = data["tags"]
        if "reading_status" in data:
            lib_entry.reading_status = data["reading_status"]
        if "importance_rating" in data:
            lib_entry.importance_rating = data["importance_rating"]

        lib_entry.save()

        return JsonResponse({"success": True, "message": "Paper updated successfully"})
    except UserLibrary.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Paper not found in library"}, status=404
        )
    except Exception as e:
        logger.error(f"Error updating library paper: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def api_remove_library_paper(request, paper_id):
    """API endpoint to remove paper from library"""
    try:
        paper_id = UUID(str(paper_id))

        lib_entry = UserLibrary.objects.get(user=request.user, paper_id=paper_id)

        paper_title = lib_entry.paper.title
        lib_entry.delete()

        messages.success(request, f"Paper '{paper_title}' removed from library")

        return JsonResponse({"success": True, "message": "Paper removed from library"})
    except UserLibrary.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Paper not found in library"}, status=404
        )
    except Exception as e:
        logger.error(f"Error removing library paper: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_library_paper_bibtex(request, paper_id):
    """Generate BibTeX for a single library paper on demand.

    GET /api/library/papers/<paper_id>/bibtex/

    Returns BibTeX text generated via scitex.scholar.formatting.
    """
    try:
        from scitex.scholar.formatting import to_bibtex

        paper_id = UUID(str(paper_id))
        entry = UserLibrary.objects.select_related("paper").get(
            user=request.user, paper_id=paper_id
        )
        p = entry.paper

        if p and p.bibtex_content:
            bibtex = p.bibtex_content
        elif p:
            paper_dict = {
                "title": p.title or "",
                "authors_str": p.authors or "",
                "year": str(p.publication_date.year) if p.publication_date else "",
                "journal": str(p.journal) if p.journal else "",
                "doi": p.doi or "",
                "pmid": p.pmid or "",
                "arxiv_id": p.arxiv_id or "",
                "abstract": getattr(p, "abstract", "") or "",
                "document_type": "article",
            }
            bibtex = to_bibtex(paper_dict)
        else:
            return JsonResponse({"error": "Paper not found"}, status=404)

        return JsonResponse({"bibtex": bibtex})

    except UserLibrary.DoesNotExist:
        return JsonResponse({"error": "Paper not in library"}, status=404)
    except Exception as e:
        logger.error(f"Error generating BibTeX: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_library_export_named_bib(request):
    """Export selected library papers as a named .bib file.

    POST /api/library/export-named-bib/
    Body: {"paper_ids": [...], "query": "search query"}

    Filename is sanitized from query. Delegates to scitex.scholar.formatting.
    """
    try:
        from django.http import HttpResponse
        from scitex.scholar.formatting import sanitize_filename, to_bibtex

        data = json.loads(request.body)
        paper_ids = data.get("paper_ids", [])
        query = data.get("query", "library_export")

        if not paper_ids:
            return JsonResponse({"error": "paper_ids required"}, status=400)

        entries = UserLibrary.objects.filter(
            user=request.user, paper_id__in=paper_ids
        ).select_related("paper")

        bibtex_parts = []
        for entry in entries:
            p = entry.paper
            if not p:
                continue
            if p.bibtex_content:
                bibtex_parts.append(p.bibtex_content.strip())
            else:
                paper_dict = {
                    "title": p.title or "",
                    "authors_str": p.authors or "",
                    "year": str(p.publication_date.year) if p.publication_date else "",
                    "journal": str(p.journal) if p.journal else "",
                    "doi": p.doi or "",
                    "pmid": p.pmid or "",
                    "arxiv_id": p.arxiv_id or "",
                    "abstract": getattr(p, "abstract", "") or "",
                    "document_type": "article",
                }
                bibtex_parts.append(to_bibtex(paper_dict).strip())

        combined = "\n\n".join(bibtex_parts)
        filename = sanitize_filename(query) + ".bib"

        response = HttpResponse(combined, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error exporting named bib: {e}")
        return JsonResponse({"error": str(e)}, status=500)


# EOF
