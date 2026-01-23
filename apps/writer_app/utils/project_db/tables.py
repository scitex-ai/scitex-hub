#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Table-related database operations for ProjectDatabase.
"""

import json
import time
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class TableOperations:
    """Table-related database operations."""

    def __init__(self, db):
        """
        Initialize with database instance.

        Args:
            db: ProjectDatabase instance
        """
        self.db = db

    def upsert(self, metadata: dict):
        """
        Insert or update table metadata.

        Args:
            metadata: Dictionary with keys:
                - file_path: Relative path from project root
                - file_name: Just the filename
                - file_hash: SHA256 hash for change detection
                - caption: Table caption (optional)
                - last_modified: Unix timestamp
                - tags: List of tags (optional)
                - is_referenced: Boolean (optional, default False)
                - reference_count: Integer (optional, default 0)
                - source: Category (paper, pool, data, scripts)
                - location: Directory path
        """
        with self.db.connection() as conn:
            conn.execute('''
                INSERT INTO tables (
                    file_path, file_name, file_hash, caption,
                    last_modified, thumbnail_path, tags,
                    is_referenced, reference_count,
                    source, location, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_name = excluded.file_name,
                    file_hash = excluded.file_hash,
                    caption = excluded.caption,
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
                metadata.get('caption'),
                metadata['last_modified'],
                metadata.get('thumbnail_path'),
                json.dumps(metadata.get('tags', [])),
                metadata.get('is_referenced', 0),
                metadata.get('reference_count', 0),
                metadata['source'],
                metadata['location'],
                time.time()
            ))

    def get_all(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get all tables with optional filters.

        Args:
            filters: Optional dictionary with keys:
                - source: Filter by source (paper, pool, data, scripts)
                - is_referenced: Filter by reference status (True/False)

        Returns:
            List of table dictionaries
        """
        query = 'SELECT * FROM tables WHERE 1=1'
        params = []

        if filters:
            if filters.get('source'):
                query += ' AND source = ?'
                params.append(filters['source'])

            if filters.get('is_referenced') is not None:
                query += ' AND is_referenced = ?'
                params.append(int(filters['is_referenced']))

        query += ' ORDER BY last_modified DESC'

        with self.db.connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            tables = []
            for row in rows:
                table = dict(row)
                # Parse JSON tags
                table['tags'] = json.loads(table['tags']) if table['tags'] else []
                tables.append(table)

            logger.debug(f"[ProjectDB] Retrieved {len(tables)} tables")
            return tables

    def delete(self, file_path: str):
        """
        Delete table from database.

        Args:
            file_path: Relative file path
        """
        with self.db.connection() as conn:
            conn.execute('DELETE FROM tables WHERE file_path = ?', (file_path,))
            logger.debug(f"[ProjectDB] Deleted table: {file_path}")


# EOF
