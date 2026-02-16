#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consolidated citation formatters — single source of truth.

All BibTeX, RIS, and EndNote formatting routes through this module.
Callers convert their data source (ORM, dict) to a standard paper dict
using ``paper_from_orm()`` or ``paper_from_dict()``, then call the
format functions (``to_bibtex``, ``to_ris``, ``to_endnote``, etc.).
"""

from __future__ import annotations

import re
from typing import List

# ── Normalisation ────────────────────────────────────────────────


def clean_text(text: str) -> str:
    """Remove characters that break citation formats and normalise whitespace."""
    if not text:
        return ""
    text = re.sub(r"[{}\[\]\\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


_DOC_TYPE_TO_ENTRY = {
    "article": "article",
    "preprint": "misc",
    "book": "book",
    "chapter": "inbook",
    "conference": "inproceedings",
    "thesis": "phdthesis",
    "report": "techreport",
    "dataset": "misc",
}

_DOC_TYPE_TO_RIS = {
    "article": "JOUR",
    "book": "BOOK",
    "chapter": "CHAP",
    "conference": "CONF",
    "thesis": "THES",
}

_DOC_TYPE_TO_ENDNOTE = {
    "article": "Journal Article",
    "book": "Book",
    "chapter": "Book Section",
    "conference": "Conference Paper",
    "thesis": "Thesis",
}


def generate_cite_key(paper: dict) -> str:
    """Generate a BibTeX citation key from a paper dict."""
    authors = paper.get("authors_str") or "unknown"
    first_author = authors.split(",")[0].split()[-1] if authors else "unknown"
    first_author = re.sub(r"[^a-zA-Z]", "", first_author).lower()
    year = str(paper.get("year") or "XXXX")
    return f"{first_author}{year}"


def paper_from_orm(paper) -> dict:
    """Convert a SearchIndex ORM instance to a standard paper dict.

    Handles the Author M2M relation via ``AuthorPaper``.
    """
    # Format authors from M2M
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


def paper_from_dict(data: dict) -> dict:
    """Normalise a plain dict (e.g. API search result) to a standard paper dict."""
    return {
        "title": data.get("title") or "Unknown",
        "authors_str": data.get("authors") or data.get("author") or "",
        "journal": (data.get("journal") or "").replace(r"\s*\(IF.*\)", ""),
        "year": str(data.get("year") or ""),
        "doi": data.get("doi") or data.get("DOI") or "",
        "pmid": data.get("pmid") or "",
        "arxiv_id": data.get("arxiv_id") or "",
        "url": (
            data.get("externalUrl")
            or data.get("external_url")
            or data.get("url")
            or data.get("pdf_url")
            or ""
        ),
        "abstract": data.get("abstract") or data.get("snippet") or "",
        "document_type": data.get("document_type") or "article",
        "citation_count": data.get("citations") or data.get("citation_count") or 0,
        "impact_factor": data.get("impact_factor") or 0,
        "is_open_access": data.get("is_open_access", False),
        "source": data.get("source") or "unknown",
        "volume": data.get("volume") or "",
        "number": data.get("number") or "",
        "pages": data.get("pages") or "",
    }


# ── BibTeX ───────────────────────────────────────────────────────


def to_bibtex(paper: dict) -> str:
    """Format a standard paper dict as a BibTeX entry."""
    doc_type = paper.get("document_type", "article")
    entry_type = _DOC_TYPE_TO_ENTRY.get(doc_type, "article")
    key = paper.get("cite_key") or generate_cite_key(paper)

    lines = [f"@{entry_type}{{{key},"]

    title = clean_text(paper.get("title") or "")
    if title:
        lines.append(f"  title = {{{title}}},")

    authors = paper.get("authors_str") or ""
    lines.append(f"  author = {{{authors or 'Unknown'}}},")

    journal = clean_text(paper.get("journal") or "")
    if journal:
        lines.append(f"  journal = {{{journal}}},")
    if paper.get("year"):
        lines.append(f"  year = {{{paper['year']}}},")
    for field in ("volume", "number", "pages"):
        if paper.get(field):
            lines.append(f"  {field} = {{{paper[field]}}},")
    if paper.get("doi"):
        lines.append(f"  doi = {{{paper['doi']}}},")
    if paper.get("pmid"):
        lines.append(f"  pmid = {{{paper['pmid']}}},")
    if paper.get("arxiv_id"):
        lines.append(f"  eprint = {{{paper['arxiv_id']}}},")
        lines.append("  archivePrefix = {arXiv},")
    if paper.get("url"):
        lines.append(f"  url = {{{paper['url']}}},")
    if paper.get("abstract"):
        abstract = clean_text(paper["abstract"])
        if len(abstract) > 500:
            abstract = abstract[:500] + "..."
        lines.append(f"  abstract = {{{abstract}}},")

    # Remove trailing comma from last field
    if lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]
    lines.append("}")
    return "\n".join(lines)


# ── RIS ──────────────────────────────────────────────────────────


def to_ris(paper: dict) -> str:
    """Format a standard paper dict as a RIS entry."""
    doc_type = paper.get("document_type", "article")
    ris_type = _DOC_TYPE_TO_RIS.get(doc_type, "GEN")
    lines = [f"TY  - {ris_type}"]

    title = clean_text(paper.get("title") or "")
    if title:
        lines.append(f"TI  - {title}")

    authors = paper.get("authors_str") or ""
    if authors:
        for author in re.split(r"\s+and\s+|,\s*", authors):
            author = author.strip()
            if author:
                lines.append(f"AU  - {author}")

    journal = clean_text(paper.get("journal") or "")
    if journal:
        lines.append(f"JO  - {journal}")
    if paper.get("year"):
        lines.append(f"PY  - {paper['year']}")
    if paper.get("doi"):
        lines.append(f"DO  - {paper['doi']}")
    if paper.get("url"):
        lines.append(f"UR  - {paper['url']}")
    if paper.get("abstract"):
        abstract = clean_text(paper["abstract"])
        if len(abstract) > 1000:
            abstract = abstract[:1000] + "..."
        lines.append(f"AB  - {abstract}")

    lines.append("ER  - ")
    return "\n".join(lines)


# ── EndNote ──────────────────────────────────────────────────────


def to_endnote(paper: dict) -> str:
    """Format a standard paper dict as an EndNote entry."""
    doc_type = paper.get("document_type", "article")
    endnote_type = _DOC_TYPE_TO_ENDNOTE.get(doc_type, "Generic")
    lines = [f"%0 {endnote_type}"]

    title = clean_text(paper.get("title") or "")
    if title:
        lines.append(f"%T {title}")

    authors = paper.get("authors_str") or ""
    if authors:
        for author in re.split(r"\s+and\s+|,\s*", authors):
            author = author.strip()
            if author:
                lines.append(f"%A {author}")

    journal = clean_text(paper.get("journal") or "")
    if journal:
        lines.append(f"%J {journal}")
    if paper.get("year"):
        lines.append(f"%D {paper['year']}")
    if paper.get("doi"):
        lines.append(f"%R {paper['doi']}")
    if paper.get("url"):
        lines.append(f"%U {paper['url']}")
    if paper.get("abstract"):
        abstract = clean_text(paper["abstract"])
        if len(abstract) > 1000:
            abstract = abstract[:1000] + "..."
        lines.append(f"%X {abstract}")

    return "\n".join(lines)


# ── CSV ──────────────────────────────────────────────────────────


def to_csv_row(paper: dict) -> dict:
    """Format a standard paper dict as a CSV row dict."""
    return {
        "Title": clean_text(paper.get("title") or ""),
        "Authors": paper.get("authors_str") or "",
        "Journal": clean_text(paper.get("journal") or ""),
        "Year": paper.get("year") or "",
        "DOI": paper.get("doi") or "",
        "PMID": paper.get("pmid") or "",
        "URL": paper.get("url") or "",
        "Abstract": clean_text(paper.get("abstract") or ""),
    }


# ── Batch helpers ────────────────────────────────────────────────

_FORMAT_FUNCS = {
    "bibtex": to_bibtex,
    "ris": to_ris,
    "endnote": to_endnote,
}

FORMAT_EXTENSIONS = {
    "bibtex": ".bib",
    "endnote": ".enw",
    "ris": ".ris",
    "csv": ".csv",
    "json": ".json",
}


def papers_to_format(papers: List[dict], fmt: str) -> str:
    """Format a list of paper dicts to the given format string."""
    func = _FORMAT_FUNCS.get(fmt)
    if not func:
        raise ValueError(f"Unsupported format: {fmt}. Use: {', '.join(_FORMAT_FUNCS)}")
    return "\n\n".join(func(p) for p in papers)


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
