"""
Citation Graph Service

Business logic layer for citation network analysis.
Wraps the scitex.scholar.citation_graph module with caching and error handling.
"""

import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional

from django.conf import settings
from django.core.cache import cache

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
        db_path = getattr(settings, "CROSSREF_DB_PATH", None)

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
                cached["cached"] = True
                return cached

        # Get from database
        try:
            summary = self.builder.get_paper_summary(doi)
            if summary:
                # Cache for 1 hour
                cache.set(cache_key, summary, 3600)
                summary["cached"] = False
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
        use_cache: bool = True,
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
            "network",
            doi,
            top_n=top_n,
            wc=weight_coupling,
            wco=weight_cocitation,
            wd=weight_direct,
        )

        # Check cache
        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for citation network: {doi}")
                cached["metadata"]["cached"] = True
                return cached

        # Build network
        try:
            logger.info(f"Building citation network for {doi} (top_n={top_n})")
            graph = self.builder.build(
                seed_doi=doi,
                top_n=top_n,
                weight_coupling=weight_coupling,
                weight_cocitation=weight_cocitation,
                weight_direct=weight_direct,
            )

            # Convert to dict
            result = graph.to_dict()
            result["metadata"]["cached"] = False
            result["metadata"]["build_time"] = None  # Could add timing here

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
        self, doi: str, limit: int = 10, use_cache: bool = True
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
        network = self.build_network(doi=doi, top_n=limit, use_cache=use_cache)

        # Extract and sort nodes
        nodes = sorted(
            network["nodes"], key=lambda n: n.get("similarity_score", 0), reverse=True
        )

        # Remove seed paper
        related = [n for n in nodes if n["id"].lower() != doi.lower()]

        return related[:limit]

    def health_check(self) -> Dict:
        """
        Check service health with caching to prevent flood attacks.

        Health status is cached for 30 seconds to reduce database load.

        Returns:
            Dictionary with health status
        """
        # Check cache first (30 second TTL prevents flood attacks)
        cache_key = "citation_graph:health_status"
        cached_status = cache.get(cache_key)
        if cached_status:
            cached_status["cached"] = True
            return cached_status

        try:
            # Try to get a sample paper
            test_doi = "10.1038/s41586-020-2008-3"
            summary = self.get_paper_summary(test_doi, use_cache=False)

            if summary:
                result = {
                    "status": "healthy",
                    "database": self.db_path,
                    "database_accessible": True,
                    "cached": False,
                }
            else:
                result = {
                    "status": "degraded",
                    "database": self.db_path,
                    "database_accessible": True,
                    "warning": "Test DOI not found",
                    "cached": False,
                }

            # Cache for 30 seconds
            cache.set(cache_key, result, 30)
            return result

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            result = {
                "status": "unhealthy",
                "database": self.db_path,
                "database_accessible": False,
                "error": str(e),
                "cached": False,
            }
            # Cache failures for 10 seconds (shorter to allow recovery detection)
            cache.set(cache_key, result, 10)
            return result


# Service mode: 'local_db', 'http', 'proxy', or None (not yet determined)
_service_mode = None


class CitationGraphHTTPService(CitationGraphService):
    """
    Citation graph service using crossref-local HTTP API.

    Uses CitationGraphBuilder with api_url instead of db_path.
    Inherits caching and error handling from CitationGraphService.
    """

    def __init__(self, api_url: str):
        """Initialize service with crossref-local HTTP API URL."""
        self.api_url = api_url
        self.db_path = None
        self.builder = None
        self._initialize_builder_http()

    def _initialize_builder_http(self):
        """Initialize the CitationGraphBuilder with HTTP mode."""
        from scitex.scholar.citation_graph import CitationGraphBuilder

        self.builder = CitationGraphBuilder(api_url=self.api_url)
        logger.info(f"Citation graph builder initialized with HTTP: {self.api_url}")

    def health_check(self) -> Dict:
        """Check service health via crossref-local HTTP API."""
        cache_key = "citation_graph:health_status"
        cached_status = cache.get(cache_key)
        if cached_status:
            cached_status["cached"] = True
            return cached_status

        try:
            from crossref_local.remote import RemoteClient

            client = RemoteClient(self.api_url)
            health = client.health(timeout=5)

            result = {
                "status": "healthy",
                "mode": "http",
                "api_url": self.api_url,
                "database_accessible": True,
                "cached": False,
            }
            cache.set(cache_key, result, 30)
            return result

        except Exception as e:
            logger.error(f"HTTP health check failed: {e}")
            result = {
                "status": "unhealthy",
                "mode": "http",
                "api_url": self.api_url,
                "database_accessible": False,
                "error": str(e),
                "cached": False,
            }
            cache.set(cache_key, result, 10)
            return result


def _detect_crossref_http_url() -> Optional[str]:
    """
    Detect crossref-local HTTP API URL from environment or Django settings.

    Checks in order:
    1. CROSSREF_LOCAL_API_URL env var
    2. settings.CROSSREF_LOCAL_API_URL
    3. settings.CROSSREF_INTERNAL_URL (Docker service name, e.g. http://crossref:31291)
    4. http://localhost:31291 (default)

    Returns:
        API URL string if available and reachable, None otherwise
    """
    import os

    try:
        from crossref_local._core.config import DEFAULT_API_URL
    except ImportError:
        DEFAULT_API_URL = None

    candidates = [
        os.environ.get("CROSSREF_LOCAL_API_URL"),
        getattr(settings, "CROSSREF_LOCAL_API_URL", None),
        getattr(settings, "CROSSREF_INTERNAL_URL", None),
        DEFAULT_API_URL,
    ]

    try:
        from crossref_local.remote import RemoteClient

        for url in candidates:
            if not url:
                continue
            try:
                client = RemoteClient(url)
                if client.is_reachable(timeout=3):
                    logger.debug(f"crossref-local HTTP reachable at {url}")
                    return url
            except (ConnectionError, OSError):
                continue
    except ImportError as e:
        logger.debug(f"crossref_local package not available: {e}")

    return None


def get_citation_graph_service():
    """
    Get citation graph service instance.

    Fallback chain:
    1. Local SQLite database (fastest, requires local DB file)
    2. crossref-local HTTP API (localhost:31291, requires running server)
    3. Remote proxy (scitex.ai, slowest fallback)

    Returns:
        CitationGraphService, CitationGraphHTTPService, or CitationGraphProxyService
    """
    global _service_mode

    # Use cached mode decision
    if _service_mode == "proxy":
        from .proxy import CitationGraphProxyService

        return CitationGraphProxyService()
    if _service_mode == "http":
        url = _detect_crossref_http_url()
        if url:
            return CitationGraphHTTPService(url)
        # HTTP no longer available, reset
        _service_mode = None

    # 1. Try local SQLite database
    if _service_mode != "http":
        try:
            service = CitationGraphService()
            _service_mode = "local_db"
            logger.info("Using local citation graph service (SQLite)")
            return service
        except (FileNotFoundError, ImportError) as e:
            logger.debug(f"Local DB not available: {e}")

    # 2. Try crossref-local HTTP API
    http_url = _detect_crossref_http_url()
    if http_url:
        _service_mode = "http"
        logger.info(f"Using crossref-local HTTP service: {http_url}")
        return CitationGraphHTTPService(http_url)

    # 3. Fall back to proxy
    logger.warning("No local service available, using proxy")
    from .proxy import CitationGraphProxyService

    _service_mode = "proxy"
    return CitationGraphProxyService()
