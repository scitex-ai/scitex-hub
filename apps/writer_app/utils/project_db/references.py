#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reference tracking operations for ProjectDatabase.
"""

import logging

logger = logging.getLogger(__name__)


class ReferenceOperations:
    """LaTeX reference tracking operations."""

    def __init__(self, db):
        """
        Initialize with database instance.

        Args:
            db: ProjectDatabase instance
        """
        self.db = db

    def update_references(self, figure_id: int, is_referenced: bool, reference_count: int):
        """
        Update reference status for a figure.

        Args:
            figure_id: Figure ID
            is_referenced: Whether figure is referenced
            reference_count: Number of references
        """
        with self.db.connection() as conn:
            conn.execute('''
                UPDATE figures
                SET is_referenced = ?, reference_count = ?
                WHERE id = ?
            ''', (int(is_referenced), reference_count, figure_id))

    def add_latex_reference(self, figure_id: int, tex_file: str, line_number: int = None, context: str = None):
        """
        Add a LaTeX reference record.

        Args:
            figure_id: Figure ID
            tex_file: Path to .tex file
            line_number: Line number (optional)
            context: Context text (optional)
        """
        with self.db.connection() as conn:
            conn.execute('''
                INSERT INTO latex_references (figure_id, tex_file, line_number, context)
                VALUES (?, ?, ?, ?)
            ''', (figure_id, tex_file, line_number, context))

    def clear_latex_references(self, figure_id: int):
        """
        Clear all LaTeX references for a figure.

        Args:
            figure_id: Figure ID
        """
        with self.db.connection() as conn:
            conn.execute('DELETE FROM latex_references WHERE figure_id = ?', (figure_id,))


# EOF
