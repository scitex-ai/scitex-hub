#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions for ProjectDatabase.
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseUtils:
    """Utility functions for database operations."""

    def __init__(self, db):
        """
        Initialize with database instance.

        Args:
            db: ProjectDatabase instance
        """
        self.db = db

    def check_if_indexed(self, file_path: str, file_hash: str, table_type: str = 'figure') -> bool:
        """
        Check if file is already indexed with same hash.

        Args:
            file_path: Relative file path
            file_hash: SHA256 hash of file
            table_type: 'figure' or 'table' (default: 'figure')

        Returns:
            True if file is indexed with same hash (no need to re-index)
        """
        table_name = 'tables' if table_type == 'table' else 'figures'
        with self.db.connection() as conn:
            cursor = conn.execute(
                f'SELECT file_hash FROM {table_name} WHERE file_path = ?',
                (file_path,)
            )
            row = cursor.fetchone()
            return row is not None and row['file_hash'] == file_hash

    def check_hash_exists(self, file_hash: str, table_type: str = 'figure') -> dict | None:
        """
        Check if a file hash already exists in the database (for duplicate detection).

        Args:
            file_hash: SHA256 hash of file
            table_type: 'figure' or 'table' (default: 'figure')

        Returns:
            Dictionary with file info if hash exists, None otherwise
        """
        table_name = 'tables' if table_type == 'table' else 'figures'
        with self.db.connection() as conn:
            cursor = conn.execute(
                f'SELECT file_path, file_name, file_size FROM {table_name} WHERE file_hash = ?',
                (file_hash,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None


def get_project_db(project):
    """
    Get ProjectDatabase instance for a project.

    Args:
        project: Project model instance

    Returns:
        ProjectDatabase instance
    """
    from apps.writer_app.utils.project_db.core import ProjectDatabase

    # Determine project path based on git_clone_path or filesystem manager
    if hasattr(project, 'git_clone_path') and project.git_clone_path:
        # Use git_clone_path if available (for authenticated users)
        project_path = Path(project.git_clone_path)
        logger.debug(f"[ProjectDB] Using git_clone_path for project {project.id}: {project_path}")
    else:
        # Use ProjectFilesystemManager for visitor projects or projects without git_clone_path
        try:
            from apps.project_app.services.project_filesystem import get_project_filesystem_manager

            if not hasattr(project, 'owner') or not project.owner:
                raise ValueError(f"Project {project.id} has no owner")

            manager = get_project_filesystem_manager(project.owner)
            project_path = manager.get_project_root_path(project)

            if not project_path:
                raise ValueError(f"Project path not found for project {project.id} (slug: {project.slug})")

            logger.info(f"[ProjectDB] Using filesystem manager path for project {project.id}: {project_path}")
        except Exception as e:
            logger.error(f"[ProjectDB] Could not determine project path: {e}", exc_info=True)
            raise ValueError(f"Cannot determine project path for project {project.id}: {e}")

    return ProjectDatabase(project_path)


# EOF
