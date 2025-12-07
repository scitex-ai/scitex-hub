#!/usr/bin/env python3
"""Database interface for CrossRef Local SQLite database"""

import sqlite3
import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import contextmanager
from functools import lru_cache

import config

logger = logging.getLogger(__name__)


class CrossRefDatabase:
    """SQLite database interface for local CrossRef data"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or config.CROSSREF_DB_PATH

        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        # Test connection and log info
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get table names
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                self.tables = tables
                logger.info(f"Connected to database: {self.db_path}")
                logger.info(f"Available tables: {', '.join(tables)}")

                # Try to get count if works table exists
                if "works" in tables:
                    cursor.execute("SELECT COUNT(*) FROM works")
                    count = cursor.fetchone()[0]
                    logger.info(f"Database contains {count:,} papers")
                else:
                    logger.warning("No 'works' table found - checking for alternatives")

        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Access columns by name
        try:
            yield conn
        finally:
            conn.close()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Convert SQLite row to dictionary"""
        if row is None:
            return {}
        return dict(row)

    def _parse_json_field(self, field: Any) -> Any:
        """Parse JSON field if it's a string"""
        if isinstance(field, str):
            try:
                return json.loads(field)
            except json.JSONDecodeError:
                return field
        return field

    def _format_authors(self, authors: Any) -> List[str]:
        """
        Convert CrossRef author objects to list of strings.

        CrossRef stores authors as:
        [{"family": "Smith", "given": "John", "sequence": "first", ...}, ...]

        Returns:
            List of author names as strings: ["John Smith", "Jane Doe", ...]
        """
        if not authors:
            return []
        if isinstance(authors, str):
            return [authors]
        if isinstance(authors, list):
            result = []
            for author in authors:
                if isinstance(author, str):
                    result.append(author)
                elif isinstance(author, dict):
                    given = author.get("given", "")
                    family = author.get("family", "")
                    name = f"{given} {family}".strip()
                    if name:
                        result.append(name)
            return result
        return []

    def get_by_doi(self, doi: str) -> Optional[Dict]:
        """
        Get paper metadata by DOI

        Args:
            doi: Paper DOI

        Returns:
            Paper metadata dictionary or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Try different possible column names and table structures
            queries = [
                "SELECT * FROM works WHERE doi = ? LIMIT 1",
                "SELECT * FROM works WHERE DOI = ? LIMIT 1",
                "SELECT * FROM papers WHERE doi = ? LIMIT 1",
                "SELECT * FROM metadata WHERE doi = ? LIMIT 1",
            ]

            for query in queries:
                try:
                    cursor.execute(query, (doi,))
                    row = cursor.fetchone()
                    if row:
                        result = self._row_to_dict(row)

                        # If metadata JSON column exists, extract useful fields
                        if "metadata" in result:
                            metadata = self._parse_json_field(result["metadata"])
                            if isinstance(metadata, dict):
                                # Extract commonly used fields from JSON
                                result["title"] = metadata.get("title", [""])[0] if metadata.get("title") else ""
                                result["authors"] = self._format_authors(metadata.get("author", []))
                                date_parts = metadata.get("published", {}).get("date-parts", [[]])
                                result["year"] = date_parts[0][0] if date_parts and date_parts[0] else None
                                result["abstract"] = metadata.get("abstract", "")
                                result["container_title"] = metadata.get("container-title", [""])[0] if metadata.get("container-title") else ""

                        # Parse JSON fields if they exist as separate columns (legacy support)
                        if "authors" in result and isinstance(result["authors"], str):
                            result["authors"] = self._parse_json_field(result["authors"])
                        if "references" in result and isinstance(result["references"], str):
                            result["references"] = self._parse_json_field(result["references"])

                        return result
                except sqlite3.OperationalError:
                    continue

            return None

    def search_by_metadata(
        self,
        title: Optional[str] = None,
        year: Optional[int] = None,
        authors: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Search papers by metadata stored in JSON column

        Args:
            title: Title search term
            year: Publication year
            authors: Author name(s)
            limit: Maximum results

        Returns:
            List of paper metadata dictionaries
        """
        if limit > config.MAX_SEARCH_RESULTS:
            limit = config.MAX_SEARCH_RESULTS

        query = "SELECT * FROM works WHERE 1=1"
        params = []

        if title:
            # Search within JSON title array: $.title[0]
            query += " AND json_extract(metadata, '$.title[0]') LIKE ?"
            params.append(f"%{title}%")

        if year:
            # Extract year from nested date array: $.published.date-parts[0][0]
            query += " AND json_extract(metadata, '$.published.date-parts[0][0]') = ?"
            params.append(year)

        if authors:
            # Search within JSON author array (search in serialized JSON)
            query += " AND json_extract(metadata, '$.author') LIKE ?"
            params.append(f"%{authors}%")

        query += f" LIMIT {limit}"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    result = self._row_to_dict(row)
                    # Parse metadata JSON if present
                    if "metadata" in result:
                        metadata = self._parse_json_field(result["metadata"])
                        if isinstance(metadata, dict):
                            # Extract commonly used fields from JSON
                            result["title"] = metadata.get("title", [""])[0] if metadata.get("title") else ""
                            result["authors"] = self._format_authors(metadata.get("author", []))
                            date_parts = metadata.get("published", {}).get("date-parts", [[]])
                            result["year"] = date_parts[0][0] if date_parts and date_parts[0] else None
                    results.append(result)

                return results
            except sqlite3.OperationalError as e:
                logger.error(f"Search error: {e}")
                return []

    def get_references(self, doi: str, limit: int = 100) -> List[Dict]:
        """
        Get papers that this paper cites (references)

        Args:
            doi: Paper DOI
            limit: Maximum results

        Returns:
            List of cited paper metadata
        """
        if limit > config.DEFAULT_CITATION_LIMIT:
            limit = config.DEFAULT_CITATION_LIMIT

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if references table exists
            if "references" not in self.tables:
                # Try to get references from works table
                paper = self.get_by_doi(doi)
                if paper and "references" in paper:
                    refs = self._parse_json_field(paper["references"])
                    if isinstance(refs, list):
                        return [{"doi": ref} for ref in refs[:limit]]
                return []

            # Query references table
            try:
                cursor.execute(
                    """
                    SELECT cited_doi, w.*
                    FROM references r
                    LEFT JOIN works w ON r.cited_doi = w.doi
                    WHERE r.citing_doi = ?
                    LIMIT ?
                    """,
                    (doi, limit)
                )
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    result = self._row_to_dict(row)
                    if "authors" in result:
                        result["authors"] = self._parse_json_field(result["authors"])
                    results.append(result)

                return results
            except sqlite3.OperationalError:
                return []

    def get_citations(self, doi: str, limit: int = 100) -> List[Dict]:
        """
        Get papers that cite this paper

        Args:
            doi: Paper DOI
            limit: Maximum results

        Returns:
            List of citing paper metadata
        """
        if limit > config.DEFAULT_CITATION_LIMIT:
            limit = config.DEFAULT_CITATION_LIMIT

        with self.get_connection() as conn:
            cursor = conn.cursor()

            if "references" not in self.tables:
                return []

            try:
                cursor.execute(
                    """
                    SELECT citing_doi, w.*
                    FROM references r
                    LEFT JOIN works w ON r.citing_doi = w.doi
                    WHERE r.cited_doi = ?
                    LIMIT ?
                    """,
                    (doi, limit)
                )
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    result = self._row_to_dict(row)
                    if "authors" in result:
                        result["authors"] = self._parse_json_field(result["authors"])
                    results.append(result)

                return results
            except sqlite3.OperationalError:
                return []

    def get_citation_graph(
        self,
        doi: str,
        depth: int = 1,
        include_references: bool = True,
        include_citations: bool = True,
    ) -> Dict:
        """
        Build citation graph for a paper

        Args:
            doi: Paper DOI
            depth: Graph traversal depth (1-3)
            include_references: Include papers this one cites
            include_citations: Include papers citing this one

        Returns:
            Graph dictionary with nodes and edges
        """
        if depth > config.MAX_CITATION_DEPTH:
            depth = config.MAX_CITATION_DEPTH

        nodes = {}
        edges = []
        visited = set()

        # Get root paper
        root = self.get_by_doi(doi)
        if not root:
            return {"center_doi": doi, "nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}

        nodes[doi] = root
        visited.add(doi)

        # Build graph
        if include_references:
            refs = self.get_references(doi)
            for ref in refs:
                ref_doi = ref.get("doi")
                if ref_doi and ref_doi not in visited:
                    nodes[ref_doi] = ref
                    visited.add(ref_doi)
                    edges.append({
                        "source": doi,
                        "target": ref_doi,
                        "type": "cites"
                    })

        if include_citations:
            cites = self.get_citations(doi)
            for cite in cites:
                cite_doi = cite.get("doi")
                if cite_doi and cite_doi not in visited:
                    nodes[cite_doi] = cite
                    visited.add(cite_doi)
                    edges.append({
                        "source": cite_doi,
                        "target": doi,
                        "type": "cites"
                    })

        return {
            "center_doi": doi,
            "nodes": list(nodes.values()),
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }

    def get_journal_by_issn(self, issn: str) -> Optional[Dict]:
        """Get journal info by ISSN"""
        if "journals" not in self.tables:
            return None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT * FROM journals WHERE issn = ? LIMIT 1",
                    (issn,)
                )
                row = cursor.fetchone()
                return self._row_to_dict(row) if row else None
            except sqlite3.OperationalError:
                return None

    def get_journal_by_name(self, name: str) -> Optional[Dict]:
        """Get journal info by name"""
        if "journals" not in self.tables:
            return None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT * FROM journals WHERE name LIKE ? LIMIT 1",
                    (f"%{name}%",)
                )
                row = cursor.fetchone()
                return self._row_to_dict(row) if row else None
            except sqlite3.OperationalError:
                return None

    def batch_get_by_dois(self, dois: List[str]) -> List[Dict]:
        """Batch fetch papers by DOIs"""
        if len(dois) > config.MAX_BATCH_SIZE:
            dois = dois[:config.MAX_BATCH_SIZE]

        placeholders = ",".join("?" * len(dois))
        query = f"SELECT * FROM works WHERE doi IN ({placeholders})"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, dois)
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    result = self._row_to_dict(row)
                    if "authors" in result:
                        result["authors"] = self._parse_json_field(result["authors"])
                    results.append(result)

                return results
            except sqlite3.OperationalError as e:
                logger.error(f"Batch query error: {e}")
                return []

    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        stats = {
            "database_path": self.db_path,
            "tables": self.tables,
        }

        # Database size
        db_size = Path(self.db_path).stat().st_size / (1024 * 1024)  # MB
        stats["database_size_mb"] = round(db_size, 2)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get indices
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indices = [row[0] for row in cursor.fetchall()]
            stats["indices"] = indices

            # Papers count and year range
            if "works" in self.tables:
                try:
                    cursor.execute("SELECT COUNT(*) FROM works")
                    stats["total_papers"] = cursor.fetchone()[0]

                    cursor.execute("SELECT MIN(year), MAX(year) FROM works WHERE year IS NOT NULL")
                    min_year, max_year = cursor.fetchone()
                    if min_year and max_year:
                        stats["year_range"] = [min_year, max_year]
                except sqlite3.OperationalError:
                    pass

            # Journals count
            if "journals" in self.tables:
                try:
                    cursor.execute("SELECT COUNT(*) FROM journals")
                    stats["total_journals"] = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    pass

            # Citations count
            if "references" in self.tables:
                try:
                    cursor.execute("SELECT COUNT(*) FROM references")
                    stats["total_citations"] = cursor.fetchone()[0]
                    stats["has_citations"] = True
                except sqlite3.OperationalError:
                    stats["has_citations"] = False
            else:
                stats["has_citations"] = False

        return stats
