#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/services/export_packer.py
"""
Export packing service for Scholar app.

Handles resolving symlinks and packaging project papers for export.
"""

import io
import json
import logging
import zipfile
from datetime import datetime
from typing import Any, Dict, List

from django.contrib.auth.models import User

from ..models import Collection, LibraryExport, SearchIndex
from .citation_formats import (
    FORMAT_EXTENSIONS,
    paper_from_orm,
    to_bibtex,
    to_ris,
)

logger = logging.getLogger(__name__)


def _generate_json(paper: SearchIndex) -> Dict[str, Any]:
    """Generate JSON representation of a paper."""
    return {
        "id": str(paper.id),
        "title": paper.title,
        "journal": paper.journal.name if paper.journal else "",
        "year": paper.publication_date.year if paper.publication_date else None,
        "doi": paper.doi,
        "pmid": paper.pmid,
        "arxiv_id": paper.arxiv_id,
        "abstract": paper.abstract,
        "url": paper.external_url,
        "pdf_url": paper.pdf_url,
        "citations": paper.citation_count,
        "open_access": paper.is_open_access,
        "source": paper.source,
    }


def _format_paper(paper: SearchIndex, export_format: str):
    """Format a single paper in the given export format."""
    if export_format == "bibtex":
        return to_bibtex(paper_from_orm(paper))
    elif export_format == "ris":
        return to_ris(paper_from_orm(paper))
    elif export_format == "json":
        return _generate_json(paper)
    return ""


class ExportPackerService:
    """Service for packing and exporting papers with resolved references."""

    @staticmethod
    def pack_project(
        user: User,
        project,
        export_format: str = "bibtex",
        include_pdfs: bool = False,
        include_notes: bool = True,
    ) -> io.BytesIO:
        """
        Pack all project papers into a downloadable archive.

        Resolves all "symlinks" (project associations) to actual paper data.

        Args:
            user: User instance
            project: Project instance
            export_format: Citation format (bibtex, ris, json, csv)
            include_pdfs: Whether to include PDF files
            include_notes: Whether to include personal notes

        Returns:
            BytesIO buffer containing ZIP archive
        """
        from .library_cache import LibraryCacheService

        # Get all papers linked to this project
        library_entries = LibraryCacheService.get_project_papers(project, user)

        if not library_entries:
            logger.warning(f"No papers found for project {project.id}")

        # Create ZIP archive
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Generate citations file
            citations = []
            notes_content = []
            manifest = {
                "project_name": (
                    project.name if hasattr(project, "name") else str(project)
                ),
                "exported_at": datetime.now().isoformat(),
                "total_papers": len(library_entries),
                "format": export_format,
                "papers": [],
            }

            for entry in library_entries:
                paper = entry.paper
                paper_info = {
                    "title": paper.title,
                    "doi": paper.doi,
                    "reading_status": entry.reading_status,
                    "importance": entry.importance_rating,
                }
                manifest["papers"].append(paper_info)

                # Generate citation in requested format
                citations.append(_format_paper(paper, export_format))

                # Collect notes
                if include_notes and entry.personal_notes:
                    notes_content.append(
                        f"## {paper.title}\n\n{entry.personal_notes}\n\n---\n"
                    )

                # Include PDFs if requested and available
                if include_pdfs and entry.personal_pdf:
                    try:
                        pdf_filename = f"pdfs/{paper.doi or paper.id}.pdf"
                        zf.writestr(pdf_filename, entry.personal_pdf.read())
                    except Exception as e:
                        logger.error(f"Failed to include PDF for {paper.title}: {e}")

            # Write citations file
            ext = FORMAT_EXTENSIONS.get(export_format, ".txt")
            if export_format == "json":
                zf.writestr(f"references{ext}", json.dumps(citations, indent=2))
            else:
                zf.writestr(f"references{ext}", "\n\n".join(citations))

            # Write notes if included
            if include_notes and notes_content:
                zf.writestr("notes.md", "".join(notes_content))

            # Write manifest
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        buffer.seek(0)

        # Log export
        try:
            LibraryExport.objects.create(
                user=user,
                export_format=export_format,
                paper_count=len(library_entries),
                filter_criteria={"project_id": str(project.id)},
            )
        except Exception as e:
            logger.error(f"Failed to log export: {e}")

        return buffer

    @staticmethod
    def pack_collection(
        user: User,
        collection: Collection,
        export_format: str = "bibtex",
    ) -> io.BytesIO:
        """
        Pack all papers in a collection into a downloadable archive.

        Args:
            user: User instance
            collection: Collection instance
            export_format: Citation format

        Returns:
            BytesIO buffer containing ZIP archive
        """
        library_entries = collection.library_papers.filter(user=user).select_related(
            "paper"
        )

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            citations = []

            for entry in library_entries:
                paper = entry.paper
                citations.append(_format_paper(paper, export_format))

            ext = FORMAT_EXTENSIONS.get(export_format, ".txt")
            if export_format == "json":
                zf.writestr(f"{collection.name}{ext}", json.dumps(citations, indent=2))
            else:
                zf.writestr(f"{collection.name}{ext}", "\n\n".join(citations))

        buffer.seek(0)

        # Log export
        try:
            LibraryExport.objects.create(
                user=user,
                export_format=export_format,
                paper_count=len(library_entries),
                collection_name=collection.name,
            )
        except Exception as e:
            logger.error(f"Failed to log export: {e}")

        return buffer

    @staticmethod
    def export_selection(
        user: User,
        paper_ids: List[str],
        export_format: str = "bibtex",
    ) -> str:
        """
        Export selected papers as citations (no ZIP).

        Args:
            user: User instance
            paper_ids: List of paper UUIDs
            export_format: Citation format

        Returns:
            String containing all citations
        """
        papers = SearchIndex.objects.filter(id__in=paper_ids)
        citations = []

        for paper in papers:
            result = _format_paper(paper, export_format)
            if export_format == "json":
                citations.append(json.dumps(result))
            else:
                citations.append(result)

        return "\n\n".join(citations)


# EOF
