#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Citation export core — thin wrappers around citation_formats.

Maintains backward-compatible API for callers that use positional args.
All formatting logic lives in ``services.citation_formats``.
"""

from __future__ import annotations

import re

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ...services.citation_formats import (
    paper_from_dict,
    to_bibtex,
    to_endnote,
    to_ris,
)


@require_http_methods(["POST"])
@login_required
def export_citation(request):
    """Placeholder for export_citation — TODO: implement."""
    return JsonResponse({"error": "Not implemented"}, status=501)


def generate_citation(paper_data, format_type):
    """Generate citation in the specified format from a dict."""
    paper = paper_from_dict(paper_data)
    paper["cite_key"] = generate_citation_key(
        paper_data.get("authors", ""), paper_data.get("year", "")
    )

    dispatch = {"bibtex": to_bibtex, "endnote": to_endnote, "ris": to_ris}
    func = dispatch.get(format_type.lower())
    if func is None:
        return None
    return func(paper)


def generate_citation_key(authors, year):
    """Generate a citation key from authors string and year."""
    try:
        if authors and isinstance(authors, str):
            first_author = authors.split(",")[0].split(" and ")[0].strip()
            first_author = first_author.replace("Dr.", "").replace("Prof.", "").strip()
            last_name = first_author.split()[-1] if first_author.split() else "Unknown"
            last_name = "".join(c for c in last_name if c.isalnum())
            return f"{last_name}{year}"
        return f"Unknown{year}"
    except (IndexError, AttributeError, TypeError, ValueError):
        return f"Paper{year}"


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


def sanitize_filename(filename):
    """Sanitize filename for safe download."""
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    filename = filename[:50]
    return re.sub(r"\s+", "_", filename.strip())


def get_file_extension(format_type):
    """Get file extension for citation format."""
    extensions = {"bibtex": "bib", "endnote": "enw", "ris": "ris"}
    return extensions.get(format_type.lower(), "txt")


# EOF
