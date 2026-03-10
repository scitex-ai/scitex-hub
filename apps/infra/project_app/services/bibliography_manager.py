#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-12 19:03:16 (ywatanabe)"


"""
Bibliography Structure Manager

Delegates to scitex.template for structure setup and scitex.scholar for merging.
Django only orchestrates - no business logic here.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_bibliography_structure(project_path: Path, force: bool = False) -> dict:
    """
    Ensure bibliography directory structure exists.

    Delegates to scitex.template.setup_scholar_writer_integration().

    Args:
        project_path: Path to project git clone directory
        force: If True, recreate symlinks even if they exist

    Returns:
        dict with status and created items
    """
    try:
        from scitex.template import setup_scholar_writer_integration

        result = setup_scholar_writer_integration(project_path, force=force)

        # Convert to legacy format for backwards compatibility
        return {
            "success": result["success"],
            "directories_created": (
                [result["scholar_dir"]] if result["scholar_dir"] else []
            ),
            "files_created": [],
            "symlinks_created": (
                ["merged_scholar.bib"] if result["symlink_created"] else []
            ),
            "errors": result["errors"],
        }

    except Exception as e:
        logger.error(f"Error ensuring bibliography structure: {e}", exc_info=True)
        return {
            "success": False,
            "directories_created": [],
            "files_created": [],
            "symlinks_created": [],
            "errors": [str(e)],
        }


def regenerate_bibliography(project_path: Path, project_name: str = None) -> dict:
    """
    Regenerate merged_scholar.bib by merging all scholar .bib files with deduplication.

    Delegates to scitex.scholar.storage.BibTeXHandler.merge_bibtex_files() which handles:
    - DOI matching (most reliable)
    - Title + Author + Year fingerprinting
    - Metadata quality scoring

    NOTE: Writer bibliography merging is handled automatically by scitex.writer's merge script.
    Django only manages scholar bibliography files.

    Should be called when:
    - User clicks "Regenerate Bibliography" button in Scholar app
    - New .bib files are uploaded to Scholar
    - After scholar enrichment

    Args:
        project_path: Path to project git clone directory
        project_name: Optional project name for logging

    Returns:
        dict with status and statistics including duplicates_removed
    """
    results = {
        "success": True,
        "scholar_count": 0,
        "duplicates_removed": 0,
        "errors": [],
    }

    try:
        from scitex.scholar.storage import BibTeXHandler

        scitex_root = project_path / "scitex"

        # Ensure structure exists first (delegates to scitex.template)
        ensure_bibliography_structure(project_path)

        # ============================================================
        # MERGE SCHOLAR FILES WITH DEDUPLICATION
        # ============================================================
        # Delegate entirely to scitex.scholar - no business logic here

        scholar_bib_dir = scitex_root / "scholar" / "bib_files"
        scholar_files = [
            f for f in scholar_bib_dir.glob("*.bib") if not f.name.startswith("merged_")
        ]

        if not scholar_files:
            logger.info("No scholar BibTeX files to merge")
            return results

        merged_scholar_path = scholar_bib_dir / "merged_scholar.bib"

        # Delegate to scitex.scholar.storage.BibTeXHandler
        bibtex_handler = BibTeXHandler(project=project_name, config=None)
        merge_result = bibtex_handler.merge_bibtex_files(
            file_paths=scholar_files,
            output_path=merged_scholar_path,
            dedup_strategy="smart",
            return_details=True,
        )

        # Extract stats from scitex-python result
        stats = merge_result.get("stats", {})
        results["scholar_count"] = stats.get("unique_papers", 0)
        results["duplicates_removed"] = stats.get("duplicates_found", 0)

        logger.info(
            f"✓ Merged {len(scholar_files)} scholar files → "
            f"{results['scholar_count']} unique entries "
            f"({results['duplicates_removed']} duplicates removed)"
        )

        return results

    except Exception as e:
        logger.error(f"Error regenerating bibliography: {e}", exc_info=True)
        results["success"] = False
        results["errors"].append(str(e))
        return results


# EOF
