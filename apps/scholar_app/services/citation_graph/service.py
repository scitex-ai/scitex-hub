"""
Citation Graph Service

Business logic layer for citation network analysis.
Wraps the scitex.scholar.citation_graph module with caching and error handling.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List
from django.conf import settings
from django.core.cache import cache
import hashlib
import json

logger = logging.getLogger(__name__)


class CitationGraphService:
    """
    Service for building and analyzing citation networks.

    Provides caching, error handling, and rate limiting on top of
    the core citation_graph module.
    """

    def __init__(self):
        """Initialize service with database connection."""
        self.db_path = self._get_database_path()
        self.builder = None
        self._initialize_builder()

    def _get_database_path(self) -> str:
        """Get CrossRef database path from settings."""
        # Try settings first
        db_path = getattr(settings, 'CROSSREF_DB_PATH', None)

        if not db_path:
            # Fallback to default location
            db_path = str(Path.home() / "proj/crossref_local/data/crossref.db")

        if not Path(db_path).exists():
            logger.error(f"CrossRef database not found at: {db_path}")
            raise FileNotFoundError(f"CrossRef database not found: {db_path}")

        return db_path

    def _initialize_builder(self):
        """Initialize the CitationGraphBuilder."""
        try:
            from scitex.scholar.citation_graph import CitationGraphBuilder
            self.builder = CitationGraphBuilder(self.db_path)
            logger.info(f"Citation graph builder initialized with DB: {self.db_path}")
        except ImportError as e:
            logger.error(f"Failed to import citation_graph module: {e}")
            raise ImportError(
                "scitex.scholar.citation_graph not found. "
                "Ensure scitex-code is installed: pip install -e ~/proj/scitex-code"
            )
        except Exception as e:
            logger.error(f"Failed to initialize citation graph builder: {e}")
            raise

    def _create_cache_key(self, prefix: str, doi: str, **kwargs) -> str:
        """Create cache key from parameters."""
        key_parts = [prefix, doi.lower()]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        key_str = ":".join(key_parts)
        return f"citation_graph:{hashlib.md5(key_str.encode()).hexdigest()}"

    def get_paper_summary(self, doi: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Get summary information for a paper.

        Args:
            doi: DOI of the paper
            use_cache: Whether to use cached data (default: True)

        Returns:
            Dictionary with paper summary or None if not found
        """
        cache_key = self._create_cache_key("summary", doi)

        # Check cache
        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for paper summary: {doi}")
                cached['cached'] = True
                return cached

        # Get from database
        try:
            summary = self.builder.get_paper_summary(doi)
            if summary:
                # Cache for 1 hour
                cache.set(cache_key, summary, 3600)
                summary['cached'] = False
                return summary
            else:
                logger.warning(f"Paper not found: {doi}")
                return None
        except Exception as e:
            logger.error(f"Error getting paper summary for {doi}: {e}")
            raise

    def build_network(
        self,
        doi: str,
        top_n: int = 20,
        weight_coupling: float = 2.0,
        weight_cocitation: float = 2.0,
        weight_direct: float = 1.0,
        use_cache: bool = True
    ) -> Dict:
        """
        Build citation network graph for a paper.

        Args:
            doi: DOI of the seed paper
            top_n: Number of most similar papers to include
            weight_coupling: Weight for bibliographic coupling
            weight_cocitation: Weight for co-citation
            weight_direct: Weight for direct citations
            use_cache: Whether to use cached data

        Returns:
            Dictionary with network graph data
        """
        cache_key = self._create_cache_key(
            "network", doi,
            top_n=top_n,
            wc=weight_coupling,
            wco=weight_cocitation,
            wd=weight_direct
        )

        # Check cache
        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for citation network: {doi}")
                cached['metadata']['cached'] = True
                return cached

        # Build network
        try:
            logger.info(f"Building citation network for {doi} (top_n={top_n})")
            graph = self.builder.build(
                seed_doi=doi,
                top_n=top_n,
                weight_coupling=weight_coupling,
                weight_cocitation=weight_cocitation,
                weight_direct=weight_direct
            )

            # Convert to dict
            result = graph.to_dict()
            result['metadata']['cached'] = False
            result['metadata']['build_time'] = None  # Could add timing here

            # Cache for 1 hour
            cache.set(cache_key, result, 3600)

            logger.info(
                f"Built network for {doi}: "
                f"{len(result['nodes'])} nodes, {len(result['edges'])} edges"
            )

            return result

        except Exception as e:
            logger.error(f"Error building citation network for {doi}: {e}")
            raise

    def get_related_papers(
        self,
        doi: str,
        limit: int = 10,
        use_cache: bool = True
    ) -> List[Dict]:
        """
        Get list of related papers without full network graph.

        Lighter weight endpoint that just returns ranked similar papers.

        Args:
            doi: DOI of the paper
            limit: Maximum number of papers to return
            use_cache: Whether to use cached data

        Returns:
            List of paper dictionaries sorted by similarity
        """
        # Build small network and extract just the nodes
        network = self.build_network(
            doi=doi,
            top_n=limit,
            use_cache=use_cache
        )

        # Extract and sort nodes
        nodes = sorted(
            network['nodes'],
            key=lambda n: n.get('similarity_score', 0),
            reverse=True
        )

        # Remove seed paper
        related = [n for n in nodes if n['id'].lower() != doi.lower()]

        return related[:limit]

    def health_check(self) -> Dict:
        """
        Check service health.

        Returns:
            Dictionary with health status
        """
        try:
            # Try to get a sample paper
            test_doi = "10.1038/s41586-020-2008-3"
            summary = self.get_paper_summary(test_doi, use_cache=False)

            if summary:
                return {
                    'status': 'healthy',
                    'database': self.db_path,
                    'database_accessible': True
                }
            else:
                return {
                    'status': 'degraded',
                    'database': self.db_path,
                    'database_accessible': True,
                    'warning': 'Test DOI not found'
                }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'database': self.db_path,
                'database_accessible': False,
                'error': str(e)
            }


# Service mode tracking (not singleton - create fresh per request for DB connections)
_use_proxy = None


def get_citation_graph_service():
    """
    Get citation graph service instance.

    Creates fresh service per call to avoid stale database connections.
    Falls back to proxy service when local database is unavailable.

    Returns:
        CitationGraphService or CitationGraphProxyService instance
    """
    global _use_proxy

    # If we already know to use proxy, use it
    if _use_proxy is True:
        from .proxy import CitationGraphProxyService
        return CitationGraphProxyService()

    # Try local service first
    try:
        service = CitationGraphService()
        _use_proxy = False
        logger.info("Using local citation graph service")
        return service
    except (FileNotFoundError, ImportError) as e:
        # Fall back to proxy
        logger.warning(f"Local service unavailable ({e}), using NAS proxy")
        from .proxy import CitationGraphProxyService
        _use_proxy = True
        return CitationGraphProxyService()
