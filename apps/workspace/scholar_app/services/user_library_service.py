#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User Library Service

Manages user-level scholar library with filesystem storage and symlinks.
This service provides a central library for each user where papers are stored once
and can be linked to multiple projects via symlinks.

Architecture:
    User Library: ~/.scitex/scholar/library/papers/{doi|pmid|arxiv}/
    Project Links: {project_path}/.scitex/scholar/library/papers/ -> user library

Storage Strategy:
    - Papers stored once in user library (deduplicated)
    - Projects reference papers via symlinks
    - Django tracks paths via CharField (not FileField)
    - Delegates to scitex.scholar package for actual operations
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class UserLibraryService:
    """
    Manages user-level scholar library with symlinks.

    This service is a thin wrapper that:
    1. Determines user-specific library paths
    2. Delegates actual paper management to scitex.scholar package
    3. Ensures directory structure exists
    4. Provides simple interface for Django views/models
    """

    def __init__(self, user: User):
        """
        Initialize service for a specific user.

        Args:
            user: Django User instance
        """
        self.user = user
        self.library_path = self._get_user_library_path()
        self._ensure_structure()

    def _get_user_library_path(self) -> Path:
        """
        Get user's central library path.

        Returns:
            Path to user's library root

        Strategy:
            - Multi-user: {USER_DATA_ROOT}/users/{username}/.scitex/scholar/library/
            - Single-user: ~/.scitex/scholar/library/
        """
        if settings.USER_DATA_ROOT:
            # Multi-user deployment (Docker, cloud)
            return (
                settings.USER_DATA_ROOT
                / "users"
                / self.user.username
                / ".scitex"
                / "scholar"
                / "library"
            )
        else:
            # Single-user or use scitex package default
            return settings.SCITEX_SCHOLAR_USER_LIBRARY_ROOT

    def _ensure_structure(self):
        """Create library directory structure if it doesn't exist."""
        # Create base directories
        dirs_to_create = [
            self.library_path,
            self.library_path / "papers" / "doi",
            self.library_path / "papers" / "pmid",
            self.library_path / "papers" / "arxiv",
            self.library_path / "collections",
            self.library_path / "metadata",
        ]

        for directory in dirs_to_create:
            directory.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Ensured library structure for user {self.user.username} at {self.library_path}"
        )

    def add_paper(
        self,
        identifier: str,
        id_type: str,
        pdf_path: Optional[Path] = None,
        bibtex_content: Optional[str] = None,
    ) -> Dict[str, Path]:
        """
        Add paper to user library.

        Args:
            identifier: Paper identifier (DOI, PMID, arXiv ID)
            id_type: Type of identifier ('doi', 'pmid', 'arxiv')
            pdf_path: Optional path to PDF file to copy
            bibtex_content: Optional BibTeX content to save

        Returns:
            Dict with 'pdf' and 'bibtex' paths (relative to library root)

        Note:
            This is a Django wrapper. Actual paper management should be delegated
            to scitex.scholar package functions in future iterations.
        """
        # Normalize identifier for filesystem (replace / with _)
        safe_identifier = identifier.replace("/", "_").replace(":", "_")

        # Determine storage location
        paper_dir = self.library_path / "papers" / id_type
        paper_dir.mkdir(parents=True, exist_ok=True)

        result = {}

        # Copy PDF if provided
        if pdf_path and pdf_path.exists():
            dest_pdf = paper_dir / f"{safe_identifier}.pdf"
            if not dest_pdf.exists():
                import shutil

                shutil.copy2(pdf_path, dest_pdf)
                logger.info(f"Added PDF for {identifier} to user library")
            result["pdf"] = dest_pdf.relative_to(self.library_path)

        # Save BibTeX if provided
        if bibtex_content:
            dest_bib = paper_dir / f"{safe_identifier}.bib"
            dest_bib.write_text(bibtex_content)
            logger.info(f"Added BibTeX for {identifier} to user library")
            result["bibtex"] = dest_bib.relative_to(self.library_path)

        return result

    def get_paper_path(
        self, identifier: str, id_type: str, file_type: str = "pdf"
    ) -> Optional[Path]:
        """
        Get absolute path to paper file in user library.

        Args:
            identifier: Paper identifier
            id_type: Type of identifier ('doi', 'pmid', 'arxiv')
            file_type: File type ('pdf' or 'bib')

        Returns:
            Absolute path to file, or None if not found
        """
        safe_identifier = identifier.replace("/", "_").replace(":", "_")
        paper_path = (
            self.library_path / "papers" / id_type / f"{safe_identifier}.{file_type}"
        )

        if paper_path.exists():
            return paper_path
        return None

    def link_to_project(self, paper_rel_path: str, project_path: Path):
        """
        Create symlink in project's scholar directory pointing to user library.

        Args:
            paper_rel_path: Relative path to paper in user library (from library root)
            project_path: Absolute path to project directory

        Note:
            Creates: {project_path}/.scitex/scholar/library/papers/{filename}
            Points to: {user_library_path}/{paper_rel_path}
        """
        # Project's scholar library directory
        project_scholar_dir = (
            project_path / ".scitex" / "scholar" / "library" / "papers"
        )
        project_scholar_dir.mkdir(parents=True, exist_ok=True)

        # Source file in user library
        source_path = self.library_path / paper_rel_path
        if not source_path.exists():
            logger.warning(f"Source file not found: {source_path}")
            return

        # Symlink in project (use just filename)
        symlink_name = source_path.name
        symlink_path = project_scholar_dir / symlink_name

        # Create symlink if it doesn't exist
        if not symlink_path.exists():
            symlink_path.symlink_to(source_path)
            logger.info(f"Linked {symlink_name} to project {project_path.name}")
        else:
            logger.debug(f"Symlink already exists: {symlink_path}")

    def unlink_from_project(self, paper_filename: str, project_path: Path):
        """
        Remove symlink from project's scholar directory.

        Args:
            paper_filename: Filename of paper (e.g., '10.1000_example.pdf')
            project_path: Absolute path to project directory
        """
        symlink_path = (
            project_path / ".scitex" / "scholar" / "library" / "papers" / paper_filename
        )

        if symlink_path.is_symlink():
            symlink_path.unlink()
            logger.info(f"Unlinked {paper_filename} from project {project_path.name}")
        elif symlink_path.exists():
            logger.warning(f"File exists but is not a symlink: {symlink_path}")

    def list_user_papers(self) -> List[Dict]:
        """
        List all papers in user's library.

        Returns:
            List of dicts with paper info: {
                'identifier': str,
                'id_type': str,
                'pdf_path': Path,
                'bib_path': Path
            }
        """
        papers = []

        for id_type in ["doi", "pmid", "arxiv"]:
            type_dir = self.library_path / "papers" / id_type
            if not type_dir.exists():
                continue

            for pdf_file in type_dir.glob("*.pdf"):
                identifier = pdf_file.stem
                bib_file = pdf_file.with_suffix(".bib")

                papers.append(
                    {
                        "identifier": identifier,
                        "id_type": id_type,
                        "pdf_path": pdf_file,
                        "bib_path": bib_file if bib_file.exists() else None,
                    }
                )

        return papers

    def deduplicate(self) -> Dict:
        """
        Find and report duplicate papers in user library.

        Returns:
            Dict with deduplication stats: {
                'duplicates_found': int,
                'space_saved_bytes': int,
                'suggestions': List[Dict]
            }

        Note:
            This is a stub for future implementation. Actual deduplication
            logic should be delegated to scitex.scholar package.
        """
        # TODO: Implement duplicate detection using file hashes
        # TODO: Delegate to scitex.scholar.deduplicate() when available
        logger.info(f"Deduplication not yet implemented for user {self.user.username}")
        return {
            "duplicates_found": 0,
            "space_saved_bytes": 0,
            "suggestions": [],
        }


# EOF
