#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Citation export core — thin wrappers around scitex.scholar.formatting.

Maintains backward-compatible API for callers that use positional args.
All formatting logic lives in ``scitex.scholar.formatting``.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from scitex.scholar.formatting import (
    generate_cite_key,
    make_citation_key,
    paper_normalize,
    sanitize_filename,
    to_bibtex,
    to_endnote,
    to_ris,
)

__all__ = [
    "generate_cite_key",
    "make_citation_key",
    "generate_bibtex",
    "generate_endnote",
    "generate_ris",
    "get_file_extension",
    "sanitize_filename",
]


@require_http_methods(["POST"])
@login_required
def export_citation(request):
    """Placeholder for export_citation."""
    return JsonResponse({"error": "Not implemented"}, status=501)


def generate_citation(paper_data, format_type):
    """Generate citation in the specified format from a dict."""
    paper = paper_normalize(paper_data)
    paper["cite_key"] = generate_cite_key(paper)

    dispatch = {"bibtex": to_bibtex, "endnote": to_endnote, "ris": to_ris}
    func = dispatch.get(format_type.lower())
    if func is None:
        return None
    return func(paper)


def generate_bibtex(
    citation_key, title, authors, journal, year, doi, url, volume, pages, pmid
):
    """Generate BibTeX citation from positional args (legacy API)."""
    paper = {
        "cite_key": citation_key,
        "title": title,
        "authors_str": authors,
        "journal": journal,
        "year": str(year) if year else "",
        "doi": doi or "",
        "url": url or "",
        "volume": volume or "",
        "pages": pages or "",
        "pmid": pmid or "",
    }
    return to_bibtex(paper)


def generate_endnote(title, authors, journal, year, doi, url, volume, pages, pmid):
    """Generate EndNote citation from positional args (legacy API)."""
    paper = {
        "title": title,
        "authors_str": authors,
        "journal": journal,
        "year": str(year) if year else "",
        "doi": doi or "",
        "url": url or "",
        "volume": volume or "",
        "pages": pages or "",
        "pmid": pmid or "",
    }
    return to_endnote(paper)


def generate_ris(title, authors, journal, year, doi, url, volume, pages, pmid):
    """Generate RIS citation from positional args (legacy API)."""
    paper = {
        "title": title,
        "authors_str": authors,
        "journal": journal,
        "year": str(year) if year else "",
        "doi": doi or "",
        "url": url or "",
        "volume": volume or "",
        "pages": pages or "",
        "pmid": pmid or "",
    }
    return to_ris(paper)


def get_file_extension(format_type):
    """Get file extension for citation format."""
    extensions = {"bibtex": "bib", "endnote": "enw", "ris": "ris"}
    return extensions.get(format_type.lower(), "txt")


# EOF
