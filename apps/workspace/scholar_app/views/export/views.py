#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export views for Scholar App

This module handles citation format exports (BibTeX, RIS, etc.)
All formatting delegated to citation_formats (single source of truth).
"""

import csv
import json
import logging
from io import StringIO
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from ...models import Collection
from ...models import SearchIndex as Paper
from ...services.citation_formats import (
    paper_from_orm,
    to_bibtex,
    to_csv_row,
    to_endnote,
    to_ris,
)

logger = logging.getLogger(__name__)

_FORMAT_FUNCS = {
    "bibtex": to_bibtex,
    "ris": to_ris,
    "endnote": to_endnote,
}

_FORMAT_EXT = {
    "bibtex": ".bib",
    "ris": ".ris",
    "endnote": ".enw",
    "csv": ".csv",
}


def _get_papers(paper_ids):
    """Fetch papers by IDs with prefetch for authors/journal."""
    return Paper.objects.filter(id__in=paper_ids).prefetch_related("authors", "journal")


def _format_papers(papers, fmt):
    """Format papers into citation string using shared formatter."""
    func = _FORMAT_FUNCS.get(fmt)
    if not func:
        raise ValueError(f"Unsupported format: {fmt}")
    return "\n".join(func(paper_from_orm(p)) for p in papers)


@login_required
@require_http_methods(["GET"])
def export_bibtex(request):
    """Export papers as BibTeX"""
    try:
        paper_ids = request.GET.get("paper_ids", "").split(",")
        if not paper_ids or paper_ids == [""]:
            return JsonResponse(
                {"success": False, "error": "No papers specified"}, status=400
            )

        content = _format_papers(_get_papers(paper_ids), "bibtex")
        response = HttpResponse(content, content_type="text/plain")
        response["Content-Disposition"] = 'attachment; filename="papers.bib"'
        return response

    except Exception as e:
        logger.error(f"Error exporting BibTeX: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def export_ris(request):
    """Export papers as RIS"""
    try:
        paper_ids = request.GET.get("paper_ids", "").split(",")
        if not paper_ids or paper_ids == [""]:
            return JsonResponse(
                {"success": False, "error": "No papers specified"}, status=400
            )

        content = _format_papers(_get_papers(paper_ids), "ris")
        response = HttpResponse(content, content_type="text/plain")
        response["Content-Disposition"] = 'attachment; filename="papers.ris"'
        return response

    except Exception as e:
        logger.error(f"Error exporting RIS: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def export_endnote(request):
    """Export papers as EndNote"""
    try:
        paper_ids = request.GET.get("paper_ids", "").split(",")
        if not paper_ids or paper_ids == [""]:
            return JsonResponse(
                {"success": False, "error": "No papers specified"}, status=400
            )

        content = _format_papers(_get_papers(paper_ids), "endnote")
        response = HttpResponse(content, content_type="text/plain")
        response["Content-Disposition"] = 'attachment; filename="papers.enw"'
        return response

    except Exception as e:
        logger.error(f"Error exporting EndNote: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def export_csv(request):
    """Export papers as CSV"""
    try:
        paper_ids = request.GET.get("paper_ids", "").split(",")
        if not paper_ids or paper_ids == [""]:
            return JsonResponse(
                {"success": False, "error": "No papers specified"}, status=400
            )

        papers = _get_papers(paper_ids)
        output = StringIO()
        fieldnames = [
            "Title",
            "Authors",
            "Journal",
            "Year",
            "DOI",
            "PMID",
            "URL",
            "Abstract",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for paper in papers:
            writer.writerow(to_csv_row(paper_from_orm(paper)))

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="papers.csv"'
        return response

    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def export_bulk_citations(request):
    """Bulk export multiple citations in different formats"""
    try:
        data = json.loads(request.body)
        format_type = data.get("format", "bibtex")
        paper_ids = data.get("paper_ids", [])

        if not paper_ids:
            return JsonResponse(
                {"success": False, "error": "No papers specified"}, status=400
            )

        if format_type not in _FORMAT_FUNCS:
            return JsonResponse(
                {"success": False, "error": f"Unsupported format: {format_type}"},
                status=400,
            )

        papers = _get_papers(paper_ids)
        content = _format_papers(papers, format_type)
        filename = f"papers{_FORMAT_EXT.get(format_type, '.txt')}"
        return JsonResponse({"success": True, "content": content, "filename": filename})

    except Exception as e:
        logger.error(f"Error bulk exporting citations: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def export_collection(request, collection_id):
    """Export all papers in a collection"""
    try:
        collection_id = UUID(str(collection_id))
        format_type = request.GET.get("format", "bibtex")

        collection = Collection.objects.get(id=collection_id, user=request.user)
        papers = collection.papers.all().prefetch_related("authors", "journal")

        if format_type in _FORMAT_FUNCS:
            content = _format_papers(papers, format_type)
            filename = f"{collection.name}{_FORMAT_EXT.get(format_type, '.txt')}"
        elif format_type == "csv":
            output = StringIO()
            fieldnames = [
                "Title",
                "Authors",
                "Journal",
                "Year",
                "DOI",
                "PMID",
                "URL",
                "Abstract",
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for paper in papers:
                writer.writerow(to_csv_row(paper_from_orm(paper)))
            content = output.getvalue()
            filename = f"{collection.name}.csv"
        else:
            return JsonResponse(
                {"success": False, "error": f"Unsupported format: {format_type}"},
                status=400,
            )

        response = HttpResponse(content, content_type="text/plain")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Collection.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Collection not found"}, status=404
        )
    except Exception as e:
        logger.error(f"Error exporting collection: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


def get_citation(request):
    """Get citation in requested format for a paper"""
    try:
        paper_id = request.GET.get("paper_id")
        format_type = request.GET.get("format", "bibtex")

        paper = Paper.objects.get(id=paper_id)
        paper_dict = paper_from_orm(paper)

        func = _FORMAT_FUNCS.get(format_type)
        if not func:
            return JsonResponse(
                {"success": False, "error": f"Unsupported format: {format_type}"},
                status=400,
            )

        return JsonResponse(
            {"success": True, "citation": func(paper_dict), "format": format_type}
        )

    except Paper.DoesNotExist:
        return JsonResponse({"success": False, "error": "Paper not found"}, status=404)
    except Exception as e:
        logger.error(f"Error getting citation: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


# EOF
