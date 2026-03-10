#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/bibtex/preview.py

"""
BibTeX Preview View

Preview BibTeX file contents before enrichment.
"""

from django.views.decorators.http import require_http_methods
from django.http import JsonResponse


@require_http_methods(["POST"])
def bibtex_preview(request):
    """Preview BibTeX file contents before enrichment (visitor allowed)."""
    import bibtexparser

    # Check if file was uploaded
    if "bibtex_file" not in request.FILES:
        return JsonResponse({"success": False, "error": "No file uploaded"}, status=400)

    bibtex_file = request.FILES["bibtex_file"]

    # Validate file extension
    if not bibtex_file.name.endswith(".bib"):
        return JsonResponse(
            {"success": False, "error": "Please upload a .bib file"}, status=400
        )

    try:
        # Read and parse BibTeX file
        content = bibtex_file.read().decode("utf-8")
        bibtex_file.seek(0)  # Reset file pointer for potential reuse

        bib_database = bibtexparser.loads(content)

        # Extract entry information
        entries = []
        for entry in bib_database.entries[:50]:  # Limit to first 50 for preview
            entries.append(
                {
                    "key": entry.get("ID", "Unknown"),
                    "type": entry.get("ENTRYTYPE", "article"),
                    "title": entry.get("title", "No title"),
                    "author": entry.get("author", "Unknown"),
                    "year": entry.get("year", "N/A"),
                    "has_abstract": bool(entry.get("abstract")),
                    "has_url": bool(entry.get("url") or entry.get("doi")),
                    "has_citations": bool(entry.get("citations")),
                }
            )

        total_entries = len(bib_database.entries)

        return JsonResponse(
            {
                "success": True,
                "filename": bibtex_file.name,
                "total_entries": total_entries,
                "entries": entries,
                "showing_limited": total_entries > 50,
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Failed to parse BibTeX file: {str(e)}"},
            status=400,
        )


# EOF
