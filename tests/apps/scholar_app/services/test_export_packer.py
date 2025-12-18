#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/scholar_app/services/export_packer.py"""

import pytest

# from apps.scholar_app.services.export_packer import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")

if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/scholar_app/services/export_packer.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/services/export_packer.py
# """
# Export packing service for Scholar app.
# 
# Handles resolving symlinks and packaging project papers for export.
# """
# 
# import os
# import io
# import zipfile
# import json
# import logging
# from typing import Optional, List, Dict, Any
# from datetime import datetime
# from django.contrib.auth.models import User
# from ..models import SearchIndex, UserLibrary, Collection, LibraryExport
# 
# logger = logging.getLogger(__name__)
# 
# 
# class ExportPackerService:
#     """Service for packing and exporting papers with resolved references."""
# 
#     EXPORT_FORMATS = {
#         "bibtex": ".bib",
#         "endnote": ".enw",
#         "ris": ".ris",
#         "csv": ".csv",
#         "json": ".json",
#     }
# 
#     @staticmethod
#     def generate_bibtex(paper: SearchIndex) -> str:
#         """Generate BibTeX entry for a paper."""
#         # Create citation key from author and year
#         authors = paper.authors or "Unknown"
#         first_author = authors.split(",")[0].split()[-1] if authors else "Unknown"
#         year = paper.publication_date.year if paper.publication_date else "0000"
#         key = f"{first_author}{year}"
# 
#         # Determine entry type
#         entry_type = "article"
#         if paper.document_type == "preprint":
#             entry_type = "misc"
#         elif paper.document_type == "book":
#             entry_type = "book"
#         elif paper.document_type == "conference":
#             entry_type = "inproceedings"
# 
#         lines = [f"@{entry_type}{{{key},"]
#         lines.append(f'  title = {{{paper.title}}},')
#         lines.append(f'  author = {{{paper.authors or "Unknown"}}},')
# 
#         if paper.journal:
#             lines.append(f'  journal = {{{paper.journal}}},')
#         if paper.publication_date:
#             lines.append(f'  year = {{{paper.publication_date.year}}},')
#         if paper.doi:
#             lines.append(f'  doi = {{{paper.doi}}},')
#         if paper.pmid:
#             lines.append(f'  pmid = {{{paper.pmid}}},')
#         if paper.external_url:
#             lines.append(f'  url = {{{paper.external_url}}},')
#         if paper.abstract:
#             abstract = paper.abstract[:500].replace("{", "\\{").replace("}", "\\}")
#             lines.append(f'  abstract = {{{abstract}}},')
# 
#         lines.append("}")
#         return "\n".join(lines)
# 
#     @staticmethod
#     def generate_ris(paper: SearchIndex) -> str:
#         """Generate RIS entry for a paper."""
#         lines = ["TY  - JOUR"]
# 
#         lines.append(f"TI  - {paper.title}")
#         if paper.authors:
#             for author in paper.authors.split(","):
#                 lines.append(f"AU  - {author.strip()}")
#         if paper.journal:
#             lines.append(f"JO  - {paper.journal}")
#         if paper.publication_date:
#             lines.append(f"PY  - {paper.publication_date.year}")
#         if paper.doi:
#             lines.append(f"DO  - {paper.doi}")
#         if paper.abstract:
#             lines.append(f"AB  - {paper.abstract[:1000]}")
#         if paper.external_url:
#             lines.append(f"UR  - {paper.external_url}")
# 
#         lines.append("ER  -")
#         return "\n".join(lines)
# 
#     @staticmethod
#     def generate_json(paper: SearchIndex) -> Dict[str, Any]:
#         """Generate JSON representation of a paper."""
#         return {
#             "id": str(paper.id),
#             "title": paper.title,
#             "authors": paper.authors,
#             "journal": paper.journal,
#             "year": paper.publication_date.year if paper.publication_date else None,
#             "doi": paper.doi,
#             "pmid": paper.pmid,
#             "arxiv_id": paper.arxiv_id,
#             "abstract": paper.abstract,
#             "url": paper.external_url,
#             "pdf_url": paper.pdf_url,
#             "citations": paper.citation_count,
#             "open_access": paper.is_open_access,
#             "source": paper.source,
#         }
# 
#     @staticmethod
#     def pack_project(
#         user: User,
#         project,
#         export_format: str = "bibtex",
#         include_pdfs: bool = False,
#         include_notes: bool = True,
#     ) -> io.BytesIO:
#         """
#         Pack all project papers into a downloadable archive.
# 
#         Resolves all "symlinks" (project associations) to actual paper data.
# 
#         Args:
#             user: User instance
#             project: Project instance
#             export_format: Citation format (bibtex, ris, json, csv)
#             include_pdfs: Whether to include PDF files
#             include_notes: Whether to include personal notes
# 
#         Returns:
#             BytesIO buffer containing ZIP archive
#         """
#         from .library_cache import LibraryCacheService
# 
#         # Get all papers linked to this project
#         library_entries = LibraryCacheService.get_project_papers(project, user)
# 
#         if not library_entries:
#             logger.warning(f"No papers found for project {project.id}")
# 
#         # Create ZIP archive
#         buffer = io.BytesIO()
#         with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
#             # Generate citations file
#             citations = []
#             notes_content = []
#             manifest = {
#                 "project_name": project.name if hasattr(project, "name") else str(project),
#                 "exported_at": datetime.now().isoformat(),
#                 "total_papers": len(library_entries),
#                 "format": export_format,
#                 "papers": [],
#             }
# 
#             for entry in library_entries:
#                 paper = entry.paper
#                 paper_info = {
#                     "title": paper.title,
#                     "doi": paper.doi,
#                     "reading_status": entry.reading_status,
#                     "importance": entry.importance_rating,
#                 }
#                 manifest["papers"].append(paper_info)
# 
#                 # Generate citation in requested format
#                 if export_format == "bibtex":
#                     citations.append(ExportPackerService.generate_bibtex(paper))
#                 elif export_format == "ris":
#                     citations.append(ExportPackerService.generate_ris(paper))
#                 elif export_format == "json":
#                     citations.append(ExportPackerService.generate_json(paper))
# 
#                 # Collect notes
#                 if include_notes and entry.personal_notes:
#                     notes_content.append(
#                         f"## {paper.title}\n\n{entry.personal_notes}\n\n---\n"
#                     )
# 
#                 # Include PDFs if requested and available
#                 if include_pdfs and entry.personal_pdf:
#                     try:
#                         pdf_filename = f"pdfs/{paper.doi or paper.id}.pdf"
#                         zf.writestr(pdf_filename, entry.personal_pdf.read())
#                     except Exception as e:
#                         logger.error(f"Failed to include PDF for {paper.title}: {e}")
# 
#             # Write citations file
#             ext = ExportPackerService.EXPORT_FORMATS.get(export_format, ".txt")
#             if export_format == "json":
#                 zf.writestr(f"references{ext}", json.dumps(citations, indent=2))
#             else:
#                 zf.writestr(f"references{ext}", "\n\n".join(citations))
# 
#             # Write notes if included
#             if include_notes and notes_content:
#                 zf.writestr("notes.md", "".join(notes_content))
# 
#             # Write manifest
#             zf.writestr("manifest.json", json.dumps(manifest, indent=2))
# 
#         buffer.seek(0)
# 
#         # Log export
#         try:
#             LibraryExport.objects.create(
#                 user=user,
#                 export_format=export_format,
#                 paper_count=len(library_entries),
#                 filter_criteria={"project_id": str(project.id)},
#             )
#         except Exception as e:
#             logger.error(f"Failed to log export: {e}")
# 
#         return buffer
# 
#     @staticmethod
#     def pack_collection(
#         user: User,
#         collection: Collection,
#         export_format: str = "bibtex",
#     ) -> io.BytesIO:
#         """
#         Pack all papers in a collection into a downloadable archive.
# 
#         Args:
#             user: User instance
#             collection: Collection instance
#             export_format: Citation format
# 
#         Returns:
#             BytesIO buffer containing ZIP archive
#         """
#         library_entries = collection.library_papers.filter(user=user).select_related(
#             "paper"
#         )
# 
#         buffer = io.BytesIO()
#         with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
#             citations = []
# 
#             for entry in library_entries:
#                 paper = entry.paper
#                 if export_format == "bibtex":
#                     citations.append(ExportPackerService.generate_bibtex(paper))
#                 elif export_format == "ris":
#                     citations.append(ExportPackerService.generate_ris(paper))
#                 elif export_format == "json":
#                     citations.append(ExportPackerService.generate_json(paper))
# 
#             ext = ExportPackerService.EXPORT_FORMATS.get(export_format, ".txt")
#             if export_format == "json":
#                 zf.writestr(f"{collection.name}{ext}", json.dumps(citations, indent=2))
#             else:
#                 zf.writestr(f"{collection.name}{ext}", "\n\n".join(citations))
# 
#         buffer.seek(0)
# 
#         # Log export
#         try:
#             LibraryExport.objects.create(
#                 user=user,
#                 export_format=export_format,
#                 paper_count=len(library_entries),
#                 collection_name=collection.name,
#             )
#         except Exception as e:
#             logger.error(f"Failed to log export: {e}")
# 
#         return buffer
# 
#     @staticmethod
#     def export_selection(
#         user: User,
#         paper_ids: List[str],
#         export_format: str = "bibtex",
#     ) -> str:
#         """
#         Export selected papers as citations (no ZIP).
# 
#         Args:
#             user: User instance
#             paper_ids: List of paper UUIDs
#             export_format: Citation format
# 
#         Returns:
#             String containing all citations
#         """
#         papers = SearchIndex.objects.filter(id__in=paper_ids)
#         citations = []
# 
#         for paper in papers:
#             if export_format == "bibtex":
#                 citations.append(ExportPackerService.generate_bibtex(paper))
#             elif export_format == "ris":
#                 citations.append(ExportPackerService.generate_ris(paper))
#             elif export_format == "json":
#                 citations.append(json.dumps(ExportPackerService.generate_json(paper)))
# 
#         return "\n\n".join(citations)
# 
# 
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/scholar_app/services/export_packer.py
# --------------------------------------------------------------------------------
