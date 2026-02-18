#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/scholar_app/api/public_search_formatters.py
"""Export formatters for public search API (BibTeX, CSV, Text).

BibTeX formatting delegated to ``services.citation_formats``.
"""

from __future__ import annotations

import csv
import io

from scitex.scholar.formatting import paper_from_search_result as normalize_result
from scitex.scholar.formatting import paper_normalize as paper_from_dict
from scitex.scholar.formatting import to_bibtex


def to_bibtex_with_metrics(results: list[dict]) -> str:
    """Convert results to BibTeX format with citations and impact factor.

    Uses shared ``to_bibtex`` for core formatting, then appends
    metrics fields (citations, impactfactor) that are specific to
    public search results.
    """
    entries = []
    for result in results:
        paper = paper_from_dict(result)
        entry = to_bibtex(paper)

        # Append search-specific metrics before the closing brace
        metrics = []
        citations = result.get("citations") or result.get("citation_count") or 0
        metrics.append(f"  citations = {{{citations}}}")
        impact_factor = float(result.get("impact_factor") or 0)
        metrics.append(f"  impactfactor = {{{impact_factor:.1f}}}")

        if metrics:
            # Insert metrics before the closing "}"
            lines = entry.rsplit("}", 1)
            entry = lines[0].rstrip().rstrip(",") + ",\n"
            entry += ",\n".join(metrics) + "\n}"

        entries.append(entry)
    return "\n\n".join(entries)


def to_csv(results: list[dict]) -> str:
    """Convert results to CSV format with all fields."""
    output = io.StringIO()
    writer = csv.writer(output)

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
