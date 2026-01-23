#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Figure-related database operations for ProjectDatabase.
"""

import json
import time
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class FigureOperations:
    """Figure-related database operations."""

    def __init__(self, db):
        """
        Initialize with database instance.

        Args:
            db: ProjectDatabase instance
        """
        self.db = db

    def upsert(self, metadata: dict):
        """
        Insert or update figure metadata.

        Args:
            metadata: Dictionary with keys:
                - file_path: Relative path from project root
                - file_name: Just the filename
                - file_hash: SHA256 hash for change detection
                - file_size: Size in bytes
                - file_type: Extension (png, pdf, etc.)
                - last_modified: Unix timestamp
                - thumbnail_path: Relative path to thumbnail (optional)
                - tags: List of tags (optional)
                - is_referenced: Boolean (optional, default False)
                - reference_count: Integer (optional, default 0)
                - source: Category (paper, pool, data, scripts)
                - location: Directory path
        """
        with self.db.connection() as conn:
            conn.execute('''
                INSERT INTO figures (
                    file_path, file_name, file_hash, file_size, file_type,
                    last_modified, thumbnail_path, tags,
                    is_referenced, reference_count,
                    source, location, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_name = excluded.file_name,
                    file_hash = excluded.file_hash,
                    file_size = excluded.file_size,
                    last_modified = excluded.last_modified,
                    thumbnail_path = excluded.thumbnail_path,
                    tags = excluded.tags,
                    is_referenced = excluded.is_referenced,
                    reference_count = excluded.reference_count,
                    indexed_at = excluded.indexed_at
            ''', (
                metadata['file_path'],
                metadata['file_name'],
                metadata['file_hash'],
                metadata['file_size'],
                metadata['file_type'],
                metadata['last_modified'],
                metadata.get('thumbnail_path'),
                json.dumps(metadata.get('tags', [])),
                metadata.get('is_referenced', 0),
                metadata.get('reference_count', 0),
                metadata['source'],
                metadata['location'],
                time.time(),
            ))

            logger.debug(f"[ProjectDB] Upserted figure: {metadata['file_name']}")

    def get_all(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get all figures with optional filters.

        Args:
            filters: Optional dictionary with keys:
                - source: Filter by source (paper, pool, data, scripts)
                - is_referenced: Filter by reference status (True/False)
                - file_type: Filter by file type (png, pdf, etc.)

        Returns:
            List of figure dictionaries
        """
        query = 'SELECT * FROM figures WHERE 1=1'
        params = []

        if filters:
            if filters.get('source'):
                query += ' AND source = ?'
                params.append(filters['source'])

            if filters.get('is_referenced') is not None:
                query += ' AND is_referenced = ?'
                params.append(int(filters['is_referenced']))

            if filters.get('file_type'):
                query += ' AND file_type = ?'
                params.append(filters['file_type'])

        query += ' ORDER BY last_modified DESC'

        with self.db.connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            figures = []
            for row in rows:
                fig = dict(row)
                # Parse JSON tags
                fig['tags'] = json.loads(fig['tags']) if fig['tags'] else []
                figures.append(fig)

            logger.debug(f"[ProjectDB] Retrieved {len(figures)} figures")
            return figures

    def search(self, query: str) -> List[Dict]:
        """
        Full-text search across figures.

        Args:
            query: Search query string

        Returns:
            List of matching figure dictionaries
        """
        with self.db.connection() as conn:
            cursor = conn.execute('''
                SELECT figures.* FROM figures
                JOIN figures_fts ON figures.id = figures_fts.rowid
                WHERE figures_fts MATCH ?
                ORDER BY rank
            ''', (query,))

            rows = cursor.fetchall()
            figures = []
            for row in rows:
                fig = dict(row)
                fig['tags'] = json.loads(fig['tags']) if fig['tags'] else []
                figures.append(fig)

            logger.debug(f"[ProjectDB] Search '{query}' found {len(figures)} figures")
            return figures

    def delete(self, file_path: str):
        """
        Delete figure from database.

        Args:
            file_path: Relative file path
        """
        with self.db.connection() as conn:
            conn.execute('DELETE FROM figures WHERE file_path = ?', (file_path,))
            logger.debug(f"[ProjectDB] Deleted figure: {file_path}")

    def get_stats(self) -> Dict:
        """
        Get statistics about figures.

        Returns:
            Dictionary with stats:
                - total: Total number of figures
                - referenced: Number of referenced figures
                - sources: Number of distinct sources
                - total_size: Total size in bytes
        """
        with self.db.connection() as conn:
            cursor = conn.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(is_referenced) as referenced,
                    COUNT(DISTINCT source) as sources,
                    SUM(file_size) as total_size
                FROM figures
            ''')
            stats = dict(cursor.fetchone())

            # Handle NULL values
            stats['referenced'] = stats['referenced'] or 0
            stats['sources'] = stats['sources'] or 0
            stats['total_size'] = stats['total_size'] or 0

            return stats


# EOF
