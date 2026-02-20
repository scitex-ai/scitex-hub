#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consolidated citation formatters — thin wrapper around scitex.scholar.formatting.

All BibTeX, RIS, and EndNote formatting delegates to scitex.scholar.formatting.
Only ``paper_from_orm()`` lives here (Django ORM dependency).
"""

from __future__ import annotations

from scitex.scholar.formatting import (
    FORMAT_EXTENSIONS,
    clean_text,
    generate_cite_key,
    papers_to_format,
    to_bibtex,
    to_csv_row,
    to_endnote,
    to_ris,
)
from scitex.scholar.formatting import (
    paper_normalize as paper_from_dict,
)

# ── Django-specific ORM conversion ──────────────────────────────


def paper_from_orm(paper) -> dict:
    """Convert a SearchIndex ORM instance to a standard paper dict.

    Handles the Author M2M relation via ``AuthorPaper``.
    """
    try:
        author_qs = paper.authors.all().order_by("authorpaper__author_order")
        author_parts = []
        for a in author_qs:
            name = ""
            if a.last_name and a.first_name:
                name = f"{a.last_name}, {a.first_name}"
                if getattr(a, "middle_name", None):
                    name += f" {a.middle_name}"
            elif a.last_name:
                name = a.last_name
            elif getattr(a, "full_name", None):
                name = a.full_name
            if name:
                author_parts.append(name)
        authors_str = " and ".join(author_parts) if author_parts else ""
    except Exception:
        authors_str = ""

    journal_name = ""
    try:
        if paper.journal:
            journal_name = paper.journal.name
    except Exception:
        pass

    year = ""
    if paper.publication_date:
        year = str(paper.publication_date.year)

    return {
        "title": paper.title or "",
        "authors_str": authors_str,
        "journal": journal_name,
        "year": year,
        "doi": getattr(paper, "doi", "") or "",
        "pmid": getattr(paper, "pmid", "") or "",
        "arxiv_id": getattr(paper, "arxiv_id", "") or "",
        "url": getattr(paper, "external_url", "") or "",
        "abstract": getattr(paper, "abstract", "") or "",
        "document_type": getattr(paper, "document_type", "article") or "article",
        "citation_count": getattr(paper, "citation_count", 0) or 0,
    }


__all__ = [
    "clean_text",
    "generate_cite_key",
    "paper_from_orm",
    "paper_from_dict",
    "to_bibtex",
    "to_ris",
    "to_endnote",
    "to_csv_row",
    "papers_to_format",
    "FORMAT_EXTENSIONS",
]

# EOF
