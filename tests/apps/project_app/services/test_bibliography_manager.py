#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/project_app/services/bibliography_manager.py"""

import pytest

# from apps.infra.project_app.services.bibliography_manager import ...


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
# Start of Source Code from: apps/project_app/services/bibliography_manager.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # Timestamp: "2025-11-12 19:03:16 (ywatanabe)"
#
#
# """
# Bibliography Structure Manager
#
# Ensures consistent bibliography directory structure across projects.
# Handles initialization, merging, and symlink management.
# """
#
# import logging
# import os
# from pathlib import Path
#
# logger = logging.getLogger(__name__)
#
#
# def ensure_bibliography_structure(project_path: Path, force: bool = False) -> dict:
#     """
#     Ensure bibliography directory structure exists.
#
#     This is a PASSIVE operation - creates directories and symlinks,
#     but does NOT parse or merge actual BibTeX files (that's opt-in).
#
#     Args:
#         project_path: Path to project git clone directory
#         force: If True, recreate symlinks even if they exist
#
#     Returns:
#         dict with status and created items
#     """
#     results = {
#         "success": True,
#         "directories_created": [],
#         "files_created": [],
#         "symlinks_created": [],
#         "errors": [],
#     }
#
#     try:
#         scitex_root = project_path / "scitex"
#         scitex_root.mkdir(parents=True, exist_ok=True)
#
#         # ============================================================
#         # 1. CREATE SCHOLAR DIRECTORY STRUCTURE
#         # ============================================================
#         # Django only manages scholar directory
#         # Writer directory is managed exclusively by scitex.writer.Writer
#         scholar_bib_dir = scitex_root / "scholar" / "bib_files"
#         if not scholar_bib_dir.exists():
#             scholar_bib_dir.mkdir(parents=True, exist_ok=True)
#             results["directories_created"].append(
#                 str(scholar_bib_dir.relative_to(project_path))
#             )
#             logger.info(
#                 f"Created directory: {scholar_bib_dir.relative_to(project_path)}"
#             )
#
#         # ============================================================
#         # 2. CREATE SCHOLAR PLACEHOLDER FILE
#         # ============================================================
#         scholar_merged = scholar_bib_dir / "merged_scholar.bib"
#
#         placeholder_comment = """% ============================================================
# % SciTeX Scholar Bibliography
# % ============================================================
# % This file will be automatically populated when you:
# % 1. Upload BibTeX files through Scholar app, or
# % 2. Click "Regenerate Bibliography" button
# %
# % For now, this is an empty placeholder.
# % ============================================================
#
# """
#
#         # Create empty merged_scholar.bib if not exists
#         if not scholar_merged.exists():
#             scholar_merged.write_text(
#                 placeholder_comment
#                 + "% Scholar bibliography entries will appear here\n"
#             )
#             results["files_created"].append(
#                 str(scholar_merged.relative_to(project_path))
#             )
#             logger.info(f"Created placeholder: merged_scholar.bib")
#
#         # ============================================================
#         # 3. CREATE SYMLINK TO WRITER (if writer exists)
#         # ============================================================
#         # scitex/writer/00_shared/bib_files/merged_scholar.bib → ../../../scholar/bib_files/merged_scholar.bib
#         #
#         # NOTE: Writer directory structure MUST be created by scitex.writer.Writer
#         # This section only creates symlink if the structure already exists
#
#         writer_bib_dir = scitex_root / "writer" / "00_shared" / "bib_files"
#
#         if not writer_bib_dir.exists():
#             logger.info(
#                 f"Writer directory not initialized yet - skipping writer symlink"
#             )
#             logger.info(
#                 f"✓ Bibliography structure ensured for project: {project_path.name} (scholar only)"
#             )
#             return results
#
#         # Create symlink so writer's merge script can pick up scholar bibliography
#         writer_scholar_link = writer_bib_dir / "merged_scholar.bib"
#         if not writer_scholar_link.exists() or force:
#             if writer_scholar_link.exists() or writer_scholar_link.is_symlink():
#                 writer_scholar_link.unlink()
#             relative_path = os.path.relpath(scholar_merged, writer_scholar_link.parent)
#             writer_scholar_link.symlink_to(relative_path)
#             results["symlinks_created"].append(
#                 f"writer/00_shared/bib_files/merged_scholar.bib → {relative_path}"
#             )
#             logger.info(
#                 f"Created symlink: writer/00_shared/bib_files/merged_scholar.bib"
#             )
#
#         logger.info(
#             f"✓ Bibliography structure ensured for project: {project_path.name}"
#         )
#         return results
#
#     except Exception as e:
#         logger.error(f"Error ensuring bibliography structure: {e}", exc_info=True)
#         results["success"] = False
#         results["errors"].append(str(e))
#         return results
#
#
# def regenerate_bibliography(project_path: Path, project_name: str = None) -> dict:
#     """
#     Regenerate merged_scholar.bib by merging all scholar .bib files with deduplication.
#
#     This is an ACTIVE operation - actually parses and merges BibTeX files.
#     Uses scitex.scholar's DeduplicationManager for intelligent deduplication based on:
#     - DOI matching (most reliable)
#     - Title + Author + Year fingerprinting
#     - Metadata quality scoring
#
#     NOTE: Writer bibliography merging is handled automatically by scitex.writer's merge script.
#     Django only manages scholar bibliography files.
#
#     Should be called when:
#     - User clicks "Regenerate Bibliography" button in Scholar app
#     - New .bib files are uploaded to Scholar
#     - After scholar enrichment
#
#     Args:
#         project_path: Path to project git clone directory
#         project_name: Optional project name for logging
#
#     Returns:
#         dict with status and statistics including duplicates_removed
#     """
#     results = {
#         "success": True,
#         "scholar_count": 0,
#         "duplicates_removed": 0,
#         "errors": [],
#     }
#
#     try:
#         from scitex.scholar.storage import BibTeXHandler
#         from scitex.scholar.storage._DeduplicationManager import (
#             DeduplicationManager,
#         )
#
#         scitex_root = project_path / "scitex"
#         bibtex_handler = BibTeXHandler(project=project_name, config=None)
#         dedup_manager = DeduplicationManager()
#
#         # Ensure structure exists first
#         ensure_bibliography_structure(project_path)
#
#         # ============================================================
#         # MERGE SCHOLAR FILES WITH DEDUPLICATION
#         # ============================================================
#         # Django only handles scholar bibliography merging
#         # Writer merging is handled by scitex.writer's automatic merge script
#
#         scholar_bib_dir = scitex_root / "scholar" / "bib_files"
#         scholar_files = [
#             f for f in scholar_bib_dir.glob("*.bib") if not f.name.startswith("merged_")
#         ]
#
#         if not scholar_files:
#             logger.info("No scholar BibTeX files to merge")
#             return results
#
#         merged_scholar_path = scholar_bib_dir / "merged_scholar.bib"
#
#         # Parse and deduplicate scholar files using fingerprinting
#         all_papers = []
#         seen_fingerprints = {}  # fingerprint -> paper
#
#         for scholar_file in scholar_files:
#             papers = bibtex_handler.papers_from_bibtex(scholar_file)
#             for paper in papers:
#                 # Generate fingerprint using DOI or title+year
#                 # Access metadata safely with getattr
#                 doi = (
#                     getattr(paper.metadata.identifiers, "doi", None)
#                     if hasattr(paper.metadata, "identifiers")
#                     else None
#                 )
#                 title = (
#                     getattr(paper.metadata.basic, "title", None)
#                     if hasattr(paper.metadata, "basic")
#                     else None
#                 )
#                 year = (
#                     getattr(paper.metadata.basic, "year", None)
#                     if hasattr(paper.metadata, "basic")
#                     else None
#                 )
#
#                 metadata = {"doi": doi, "title": title, "year": year}
#                 fingerprint = dedup_manager._generate_paper_fingerprint(metadata)
#
#                 if fingerprint and fingerprint not in seen_fingerprints:
#                     all_papers.append(paper)
#                     seen_fingerprints[fingerprint] = paper
#                 elif fingerprint:
#                     logger.debug(
#                         f"Skipping duplicate: {paper.metadata.basic.title[:50]}"
#                     )
#                     results["duplicates_removed"] += 1
#
#         # Write deduplicated papers to merged file
#         bibtex_handler.papers_to_bibtex(all_papers, merged_scholar_path)
#         results["scholar_count"] = len(all_papers)
#         logger.info(
#             f"✓ Merged {len(scholar_files)} scholar files → {len(all_papers)} unique entries ({results['duplicates_removed']} duplicates removed)"
#         )
#
#         return results
#
#     except Exception as e:
#         logger.error(f"Error regenerating bibliography: {e}", exc_info=True)
#         results["success"] = False
#         results["errors"].append(str(e))
#         return results
#
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/project_app/services/bibliography_manager.py
# --------------------------------------------------------------------------------
