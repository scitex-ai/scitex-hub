#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core ProjectDatabase class with connection management.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
import logging

from .schema import initialize_schema, run_migrations
from .figures import FigureOperations
from .tables import TableOperations
from .references import ReferenceOperations
from .utils import DatabaseUtils

logger = logging.getLogger(__name__)


class ProjectDatabase:
    """
    Project-specific SQLite database for figures/tables metadata.

    Provides fast querying (<50ms) of figures and tables without scanning
    the file system. Database is portable and stored within the project.

    Location: {project_root}/scitex/metadata.db
    """

    def __init__(self, project_path: Path):
        """
        Initialize project database.

        Args:
            project_path: Root path of the project
        """
        self.project_path = Path(project_path)
        self.scitex_dir = self.project_path / 'scitex'
        self.db_path = self.scitex_dir / 'metadata.db'
        self.thumbnails_dir = self.scitex_dir / 'thumbnails'

        # Ensure directories exist
        self.scitex_dir.mkdir(exist_ok=True)
        self.thumbnails_dir.mkdir(exist_ok=True)

        # Initialize database
        self._initialize_db()

        # Run migrations
        self._run_migrations()

        # Initialize operation handlers
        self.figures = FigureOperations(self)
        self.tables = TableOperations(self)
        self.references = ReferenceOperations(self)
        self.utils = DatabaseUtils(self)

        logger.info(f"[ProjectDB] Initialized database at {self.db_path}")

    def _initialize_db(self):
        """Create tables if they don't exist."""
        with self.connection() as conn:
            initialize_schema(conn)

    def _run_migrations(self):
        """Run database migrations for schema updates."""
        with self.connection() as conn:
            run_migrations(conn)

    @contextmanager
    def connection(self):
        """
        Context manager for database connection.

        Yields:
            sqlite3.Connection with row_factory set to Row
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dicts
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[ProjectDB] Database error: {e}")
            raise e
        finally:
            conn.close()

    # Backward compatibility methods - delegate to operation handlers

    def upsert_figure(self, metadata: dict):
        """Insert or update figure metadata. (Backward compatibility)"""
        return self.figures.upsert(metadata)

    def get_all_figures(self, filters=None):
        """Get all figures with optional filters. (Backward compatibility)"""
        return self.figures.get_all(filters)

    def search_figures(self, query: str):
        """Full-text search across figures. (Backward compatibility)"""
        return self.figures.search(query)

    def delete_figure(self, file_path: str):
        """Delete figure from database. (Backward compatibility)"""
        return self.figures.delete(file_path)

    def get_stats(self):
        """Get statistics about figures. (Backward compatibility)"""
        return self.figures.get_stats()

    def upsert_table(self, metadata: dict):
        """Insert or update table metadata. (Backward compatibility)"""
        return self.tables.upsert(metadata)

    def get_all_tables(self, filters=None):
        """Get all tables with optional filters. (Backward compatibility)"""
        return self.tables.get_all(filters)

    def delete_table(self, file_path: str):
        """Delete table from database. (Backward compatibility)"""
        return self.tables.delete(file_path)

    def update_references(self, figure_id: int, is_referenced: bool, reference_count: int):
        """Update reference status for a figure. (Backward compatibility)"""
        return self.references.update_references(figure_id, is_referenced, reference_count)

    def add_latex_reference(self, figure_id: int, tex_file: str, line_number: int = None, context: str = None):
        """Add a LaTeX reference record. (Backward compatibility)"""
        return self.references.add_latex_reference(figure_id, tex_file, line_number, context)

    def clear_latex_references(self, figure_id: int):
        """Clear all LaTeX references for a figure. (Backward compatibility)"""
        return self.references.clear_latex_references(figure_id)

    def check_if_indexed(self, file_path: str, file_hash: str, table_type: str = 'figure') -> bool:
        """Check if file is already indexed with same hash. (Backward compatibility)"""
        return self.utils.check_if_indexed(file_path, file_hash, table_type)

    def check_hash_exists(self, file_hash: str, table_type: str = 'figure'):
        """Check if a file hash already exists in the database. (Backward compatibility)"""
        return self.utils.check_hash_exists(file_hash, table_type)


# EOF
