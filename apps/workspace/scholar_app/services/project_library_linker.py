#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Library Linker Service

Orchestrates the paper-to-project linking workflow:
- Links papers from user library to specific projects via symlinks
- Maintains UserLibrary.project FK relationships
- Syncs project BibTeX files from linked papers

Architecture:
    User Library: ~/.scitex/scholar/library/papers/{doi|pmid|arxiv}/
    Project Links: {project_path}/.scitex/scholar/library/papers/ -> user library
    BibTeX Sync: {project_path}/.scitex/scholar/project.bib

This service is a thin Django wrapper that delegates to:
- UserLibraryService for symlink management
- scitex.scholar package for BibTeX operations (future)
"""

import logging
from pathlib import Path
from typing import Dict

from django.contrib.auth.models import User
from django.db.models import QuerySet

logger = logging.getLogger(__name__)


class ProjectLibraryLinker:
    """
    Service for linking papers from user library to research projects.

    This service orchestrates:
    1. Symlink creation in project directories
    2. Database FK updates in UserLibrary
    3. Project BibTeX file synchronization
    """

    def __init__(self, user: User):
        """
        Initialize linker for a specific user.

        Args:
            user: Django User instance
        """
        self.user = user
        # Import here to avoid circular dependency
        from .user_library_service import UserLibraryService

        self.library_service = UserLibraryService(user)

    def link_paper_to_project(self, user_library_entry, project) -> Dict[str, any]:
        """
        Link a paper from user library to a project.

        Workflow:
        1. Verify paper is in user library (storage_mode=user_library)
        2. Get project's filesystem path
        3. Create symlink in project's .scitex/scholar/library/papers/
        4. Update UserLibrary.project FK
        5. Sync project's BibTeX file

        Args:
            user_library_entry: UserLibrary instance
            project: Project instance

        Returns:
            Dict with status: {
                'success': bool,
                'symlink_created': bool,
                'bibtex_synced': bool,
                'message': str
            }

        Raises:
            ValueError: If paper not in user library or user mismatch
            FileNotFoundError: If PDF not found in user library
        """
        # Verify user owns this library entry
        if user_library_entry.user != self.user:
            raise ValueError(
                f"User mismatch: entry belongs to {user_library_entry.user.username}, "
                f"not {self.user.username}"
            )

        # Verify user owns or has access to project
        if project.owner != self.user:
            # TODO: Check project collaborator permissions
            raise ValueError(
                f"User {self.user.username} does not have access to project {project.name}"
            )

        # Verify paper is in user library storage
        if user_library_entry.storage_mode != "user_library":
            raise ValueError(
                f"Paper must be in user_library storage mode, not {user_library_entry.storage_mode}"
            )

        if not user_library_entry.user_library_pdf_path:
            raise FileNotFoundError(
                f"Paper has no PDF in user library: {user_library_entry.paper.title}"
            )

        # Get project's filesystem path
        project_path = project.get_local_path()

        if not project_path.exists():
            logger.warning(
                f"Project directory does not exist, creating: {project_path}"
            )
            project_path.mkdir(parents=True, exist_ok=True)

        # Create symlink in project
        try:
            self.library_service.link_to_project(
                paper_rel_path=user_library_entry.user_library_pdf_path,
                project_path=project_path,
            )
            symlink_created = True
        except Exception as e:
            logger.error(f"Failed to create symlink: {e}")
            symlink_created = False

        # Update UserLibrary.project FK
        user_library_entry.project = project
        user_library_entry.save(update_fields=["project"])

        # Sync project BibTeX
        try:
            self.sync_project_bibtex(project)
            bibtex_synced = True
        except Exception as e:
            logger.error(f"Failed to sync BibTeX: {e}")
            bibtex_synced = False

        success = symlink_created and bibtex_synced

        return {
            "success": success,
            "symlink_created": symlink_created,
            "bibtex_synced": bibtex_synced,
            "message": (
                f"Paper linked to project {project.name}"
                if success
                else "Partial failure in linking paper"
            ),
        }

    def unlink_paper_from_project(self, user_library_entry, project) -> Dict[str, any]:
        """
        Remove paper link from project.

        Workflow:
        1. Remove symlink from project's .scitex/scholar/library/papers/
        2. Clear UserLibrary.project FK
        3. Sync project's BibTeX file (remove this paper's entry)

        Args:
            user_library_entry: UserLibrary instance
            project: Project instance

        Returns:
            Dict with status: {
                'success': bool,
                'symlink_removed': bool,
                'bibtex_synced': bool,
                'message': str
            }

        Raises:
            ValueError: If user mismatch or paper not linked to this project
        """
        # Verify user owns this library entry
        if user_library_entry.user != self.user:
            raise ValueError(
                f"User mismatch: entry belongs to {user_library_entry.user.username}, "
                f"not {self.user.username}"
            )

        # Verify paper is linked to this project
        if user_library_entry.project != project:
            raise ValueError(
                f"Paper is not linked to project {project.name}. "
                f"Current project: {user_library_entry.project.name if user_library_entry.project else 'None'}"
            )

        # Get project's filesystem path
        project_path = project.get_local_path()

        # Remove symlink
        try:
            if user_library_entry.user_library_pdf_path:
                filename = Path(user_library_entry.user_library_pdf_path).name
                self.library_service.unlink_from_project(
                    paper_filename=filename, project_path=project_path
                )
                symlink_removed = True
            else:
                logger.warning("No PDF path found, skipping symlink removal")
                symlink_removed = False
        except Exception as e:
            logger.error(f"Failed to remove symlink: {e}")
            symlink_removed = False

        # Clear UserLibrary.project FK
        user_library_entry.project = None
        user_library_entry.save(update_fields=["project"])

        # Sync project BibTeX
        try:
            self.sync_project_bibtex(project)
            bibtex_synced = True
        except Exception as e:
            logger.error(f"Failed to sync BibTeX: {e}")
            bibtex_synced = False

        success = symlink_removed and bibtex_synced

        return {
            "success": success,
            "symlink_removed": symlink_removed,
            "bibtex_synced": bibtex_synced,
            "message": (
                f"Paper unlinked from project {project.name}"
                if success
                else "Partial failure in unlinking paper"
            ),
        }

    def sync_project_bibtex(self, project) -> Dict[str, any]:
        """
        Generate/update project.bib from all papers linked to this project.

        Collects BibTeX from all UserLibrary entries with this project.

        Args:
            project: Project instance

        Returns:
            Dict with status: {
                'success': bool,
                'bibtex_path': Path,
                'paper_count': int,
                'message': str
            }

        Note:
            This is a simple implementation. Future iterations should delegate
            to scitex.scholar.bibtex package for advanced features:
            - Deduplication
            - Citation key conflict resolution
            - BibTeX validation and formatting
        """
        project_path = project.get_local_path()

        # Ensure .scitex/scholar directory exists
        scholar_dir = project_path / ".scitex" / "scholar"
        scholar_dir.mkdir(parents=True, exist_ok=True)

        bibtex_path = scholar_dir / "project.bib"

        # Import here to avoid circular dependency
        from apps.workspace.scholar_app.models import UserLibrary

        # Get all papers linked to this project for this user
        linked_papers = UserLibrary.objects.filter(
            user=self.user, project=project
        ).select_related("paper")

        # Collect BibTeX content
        bibtex_entries = []
        paper_count = 0

        for entry in linked_papers:
            # Get BibTeX from paper or user library
            bibtex_content = None

            # Try to get from SearchIndex.bibtex_content
            if entry.paper and entry.paper.bibtex_content:
                bibtex_content = entry.paper.bibtex_content
                paper_count += 1
            # Try to get from user library BibTeX file
            elif entry.user_library_bibtex_path:
                bib_path = (
                    self.library_service.library_path / entry.user_library_bibtex_path
                )
                if bib_path.exists():
                    bibtex_content = bib_path.read_text()
                    paper_count += 1

            if bibtex_content:
                bibtex_entries.append(bibtex_content.strip())

        # Write combined BibTeX file
        if bibtex_entries:
            combined_bibtex = "\n\n".join(bibtex_entries)
            bibtex_path.write_text(combined_bibtex)
            logger.info(f"Synced project.bib for {project.name}: {paper_count} papers")
            message = f"Synced {paper_count} papers to project.bib"
            success = True
        else:
            # No papers linked - create empty file
            bibtex_path.write_text("% Project bibliography - no papers linked yet\n")
            logger.info(f"Created empty project.bib for {project.name}")
            message = "No papers linked - created empty project.bib"
            success = True

        return {
            "success": success,
            "bibtex_path": bibtex_path,
            "paper_count": paper_count,
            "message": message,
        }

    def get_project_papers(self, project) -> QuerySet:
        """
        Get all papers linked to a project for this user.

        Args:
            project: Project instance

        Returns:
            QuerySet of UserLibrary entries linked to this project
        """
        # Import here to avoid circular dependency
        from apps.workspace.scholar_app.models import UserLibrary

        return (
            UserLibrary.objects.filter(user=self.user, project=project)
            .select_related("paper")
            .order_by("-saved_at")
        )

    def setup_project_workspace(self, project) -> Dict[str, str]:
        """Ensure scholar workspace exists for a project.

        Delegates to scitex.scholar.ensure_workspace().
        Returns workspace paths for display in the UI.

        Args:
            project: Project instance

        Returns:
            Dict with workspace path strings
        """
        from scitex.scholar import ensure_workspace

        project_dir = project.get_local_path()
        workspace = ensure_workspace(project_dir)

        return {
            "workspace_dir": str(workspace),
            "bib_dir": str(workspace / "bib_files"),
            "library_dir": str(workspace / "library"),
            "project_bib": str(project_dir / "scitex" / "scholar" / "project.bib"),
        }

    def get_linkable_papers(self) -> QuerySet:
        """
        Get all papers in user library that can be linked to projects.

        Returns:
            QuerySet of UserLibrary entries in user_library storage mode
        """
        # Import here to avoid circular dependency
        from apps.workspace.scholar_app.models import UserLibrary

        return (
            UserLibrary.objects.filter(user=self.user, storage_mode="user_library")
            .select_related("paper")
            .order_by("-saved_at")
        )


# EOF
