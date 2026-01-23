#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/views/editor/api/metadata/citations.py
"""Citations API endpoints."""

from __future__ import annotations
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ...auth_utils import api_login_optional, get_user_for_request

logger = logging.getLogger(__name__)


@api_login_optional
@require_http_methods(["GET"])
def citations_api(request, project_id):
    """Get all citation keys from bibliography for autocomplete.

    Returns:
        JSON with citation keys, authors, years, titles for Monaco autocomplete
    """
    try:
        from apps.project_app.models import Project
        from pathlib import Path

        # Get project
        project = Project.objects.get(id=project_id)
        user, is_visitor = get_user_for_request(request, project_id)
        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        # Get project path (handle visitor pool)
        if is_visitor:
            from apps.project_app.services.project_filesystem import get_project_filesystem_manager
            manager = get_project_filesystem_manager(user)
            visitor_dir = manager.get_project_root_path(project)
            if not visitor_dir:
                return JsonResponse(
                    {"success": False, "error": "Project path not found"}, status=404
                )
            project_path = visitor_dir / "scitex" / "writer"
        else:
            project_path = Path(project.git_clone_path) / "scitex" / "writer"

        # Path to bibliography - try multiple locations for v2.0.0-rc1
        # 1. Try manuscript bibliography (symlink to merged bibliography)
        bib_file = project_path / "01_manuscript" / "contents" / "bibliography.bib"

        # 2. If not found, try merged bibliography in 00_shared
        if not bib_file.exists():
            bib_file = project_path / "00_shared" / "bib_files" / "bibliography.bib"

        # 3. If still not found, try old location for backwards compatibility
        if not bib_file.exists():
            bib_file = Path(project.git_clone_path) / "scitex" / "bibliography_all.bib"

        logger.info(f"[Citations] Looking for bibliography at: {bib_file}")

        if not bib_file.exists():
            # Return empty list if no bibliography yet
            return JsonResponse(
                {
                    "success": True,
                    "citations": [],
                    "message": "No bibliography file found",
                }
            )

        # Parse BibTeX file using scitex.scholar
        from scitex.scholar.storage import BibTeXHandler

        bibtex_handler = BibTeXHandler()

        try:
            papers = bibtex_handler.papers_from_bibtex(bib_file)
        except Exception as e:
            logger.warning(f"[Citations] Failed to parse bibliography: {e}")
            return JsonResponse(
                {
                    "success": True,
                    "citations": [],
                    "message": f"Error parsing bibliography: {str(e)}",
                }
            )

        # Extract citation data
        citations = []
        for paper in papers:
            # Get citation key
            key = getattr(paper, "_bibtex_key", None)
            if not key:
                continue

            # Get metadata
            title = paper.metadata.basic.title or "No title"
            authors = paper.metadata.basic.authors or []
            year = paper.metadata.basic.year

            # Format author list - show up to 3 authors for better detail
            if len(authors) == 0:
                author_str = "Unknown"
            elif len(authors) == 1:
                author_str = authors[0]
            elif len(authors) == 2:
                author_str = f"{authors[0]} and {authors[1]}"
            elif len(authors) == 3:
                author_str = f"{authors[0]}, {authors[1]}, and {authors[2]}"
            else:
                # Show first author's last name
                first_author = authors[0].split()[-1] if authors[0] else "Unknown"
                author_str = f"{first_author} et al. ({len(authors)} authors)"

            # Get additional metadata
            journal = (
                getattr(paper.metadata.publication, "journal", None)
                if hasattr(paper.metadata, "publication")
                else None
            )
            impact_factor = (
                getattr(paper.metadata.publication, "impact_factor", None)
                if hasattr(paper.metadata, "publication")
                else None
            )
            citation_count = (
                getattr(paper.metadata.citations, "total", None)
                if hasattr(paper.metadata, "citations")
                else None
            )
            abstract = (
                getattr(paper.metadata.basic, "abstract", None)
                if hasattr(paper.metadata, "basic")
                else None
            )

            # Build rich documentation in markdown format
            doc_parts = [f"## {title}", ""]  # Title as heading

            # Metadata table
            metadata_lines = []
            metadata_lines.append(f"**Authors:** {author_str}")
            if year:
                metadata_lines.append(f"**Year:** {year}")
            if journal:
                journal_line = f"**Journal:** {journal}"
                if impact_factor:
                    journal_line += f" (IF: {impact_factor})"
                metadata_lines.append(journal_line)
            if citation_count:
                metadata_lines.append(f"**Citations:** {citation_count}")

            doc_parts.extend(metadata_lines)
            doc_parts.append("")  # Blank line before abstract

            # Abstract (truncated)
            if abstract:
                abstract_preview = (
                    abstract[:400] + "..." if len(abstract) > 400 else abstract
                )
                doc_parts.append("### Abstract")
                doc_parts.append(abstract_preview)

            documentation = "\n".join(doc_parts)

            # Create citation entry with rich metadata for search
            citations.append(
                {
                    "key": key,
                    "label": key,
                    "detail": f"{author_str} ({year})" if year else author_str,
                    "documentation": documentation,
                    "insertText": key,
                    # Additional fields for fuzzy search and inline display
                    "title": title,
                    "journal": journal or "",
                    "impact_factor": impact_factor,
                    "authors": authors,
                    "citation_count": citation_count or 0,
                    "abstract": abstract or "",
                }
            )

        logger.info(f"[Citations] Found {len(citations)} citations in {bib_file.name}")

        return JsonResponse(
            {"success": True, "citations": citations, "count": len(citations)}
        )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[Citations] Error: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
