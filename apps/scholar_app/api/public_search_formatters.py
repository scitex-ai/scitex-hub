#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/scholar_app/api/public_search_formatters.py
"""Export formatters for public search API (BibTeX, CSV, Text)."""

from __future__ import annotations

import csv
import io


def normalize_result(result: dict) -> dict:
    """Normalize result to standard format with all fields."""
    return {
        "title": result.get("title") or "Unknown",
        "authors": result.get("authors") or "",
        "journal": (result.get("journal") or "").replace(r"\s*\(IF.*\)", ""),
        "year": str(result.get("year") or ""),
        "doi": result.get("doi") or result.get("DOI") or "",
        "pmid": result.get("pmid") or "",
        "arxiv_id": result.get("arxiv_id") or "",
        "citations": result.get("citations") or result.get("citation_count") or 0,
        "impact_factor": result.get("impact_factor") or 0,
        "is_open_access": result.get("is_open_access", False),
        "abstract": result.get("abstract") or result.get("snippet") or "",
        "url": result.get("externalUrl")
        or result.get("external_url")
        or result.get("pdf_url")
        or "",
        "source": result.get("source") or "unknown",
    }


def generate_bibtex_key(paper: dict) -> str:
    """Generate BibTeX citation key."""
    authors = paper.get("authors") or "unknown"
    first_author = authors.split(",")[0].split(" ")[-1] if authors else "unknown"
    year = paper.get("year") or "XXXX"
    title_word = (paper.get("title") or "untitled").split(" ")[0].lower()
    title_word = "".join(c for c in title_word if c.isalpha())
    return f"{first_author.lower()}{year}{title_word}"


def to_bibtex(results: list[dict]) -> str:
    """Convert results to BibTeX format with citations and impact factor."""
    entries = []
    for result in results:
        paper = normalize_result(result)
        key = generate_bibtex_key(paper)
        entry = f"@article{{{key},\n"
        entry += f"  author = {{{paper['authors']}}},\n"
        entry += f"  title = {{{paper['title']}}},\n"
        if paper["journal"]:
            entry += f"  journal = {{{paper['journal']}}},\n"
        if paper["year"]:
            entry += f"  year = {{{paper['year']}}},\n"
        if paper["doi"]:
            entry += f"  doi = {{{paper['doi']}}},\n"
        entry += f"  citations = {{{paper['citations']}}},\n"
        impact_factor = float(paper["impact_factor"] or 0)
        entry += f"  impactfactor = {{{impact_factor:.1f}}},\n"
        if paper["abstract"]:
            abstract = paper["abstract"][:500]
            if len(paper["abstract"]) > 500:
                abstract += "..."
            entry += f"  abstract = {{{abstract}}},\n"
        entry += "}"
        entries.append(entry)
    return "\n\n".join(entries)


def to_csv(results: list[dict]) -> str:
    """Convert results to CSV format with all fields."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        [
            "Title",
            "Authors",
            "Journal",
            "Year",
            "DOI",
            "PMID",
            "arXiv ID",
            "Citations",
            "Impact Factor",
            "Open Access",
            "Source",
            "URL",
            "Abstract",
        ]
    )

    # Data rows
    for result in results:
        paper = normalize_result(result)
        impact_factor = float(paper["impact_factor"] or 0)
        writer.writerow(
            [
                paper["title"],
                paper["authors"],
                paper["journal"],
                paper["year"],
                paper["doi"],
                paper["pmid"],
                paper["arxiv_id"],
                paper["citations"],
                f"{impact_factor:.1f}",
                "Yes" if paper["is_open_access"] else "No",
                paper["source"],
                paper["url"],
                paper["abstract"][:500] if paper["abstract"] else "",
            ]
        )

    return output.getvalue()


def to_text(results: list[dict]) -> str:
    """Convert results to plain text format."""
    lines = []
    for i, result in enumerate(results, 1):
        paper = normalize_result(result)
        entry = [f"[{i}] {paper['title']}"]
        if paper["authors"]:
            entry.append(f"Authors: {paper['authors']}")
        if paper["journal"]:
            entry.append(f"Journal: {paper['journal']}")
        if paper["year"]:
            entry.append(f"Year: {paper['year']}")
        entry.append(f"Citations: {paper['citations']}")
        impact_factor = float(paper["impact_factor"] or 0)
        entry.append(f"Impact Factor: {impact_factor:.1f}")
        if paper["doi"]:
            entry.append(f"DOI: {paper['doi']}")
        if paper["url"]:
            entry.append(f"URL: {paper['url']}")
        if paper["abstract"]:
            abstract = paper["abstract"][:300]
            if len(paper["abstract"]) > 300:
                abstract += "..."
            entry.append(f"Abstract: {abstract}")
        lines.append("\n".join(entry))
    return "\n\n---\n\n".join(lines)


# EOF
