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
                .select_related("paper")
                .prefetch_related("paper__authors")
                .order_by("-saved_at")
            )
            papers = []
            for entry in entries:
                p = entry.paper
                papers.append(
                    {
                        "id": str(entry.id),
                        "paper_id": str(p.id) if p else None,
                        "title": p.title if p else "Unknown",
                        "doi": p.doi if p else None,
                        "journal": p.journal if p else None,
                        "year": (
                            p.publication_date.year
                            if p and p.publication_date
                            else None
                        ),
                        "authors": (
                            ", ".join(
                                f"{a.first_name} {a.last_name}".strip()
                                for a in p.authors.all()
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
                        "tags": entry.tags,
                        "saved_at": (
                            entry.saved_at.isoformat() if entry.saved_at else None
                        ),
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
            return JsonResponse({"success": False, "error": str(e)}, status=500)

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
        collections = Collection.objects.filter(user=request.user).values(
            "id", "name", "description"
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
def api_zotero_status(request):
    """Stub: Zotero integration not yet implemented."""
    return JsonResponse(
        {"available": False, "error": "Zotero integration not yet available"}
    )


@login_required
@require_http_methods(["GET"])
def api_connected_papers_status(request):
    """Stub: Connected Papers integration not yet implemented."""
    return JsonResponse(
        {"available": False, "error": "Connected Papers integration not yet available"}
    )


# EOF
