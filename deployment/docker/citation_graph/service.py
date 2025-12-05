#!/usr/bin/env python3
"""Citation Graph Service - Business logic layer with caching"""

import logging
import hashlib
import json
import time
from typing import Dict, List, Optional, Any
from collections import OrderedDict
from pathlib import Path

import config

logger = logging.getLogger(__name__)


class SimpleCache:
    """Simple in-memory LRU cache"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self.cache:
            self.misses += 1
            return None

        value, timestamp = self.cache[key]

        # Check if expired
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            self.misses += 1
            return None

        # Move to end (mark as recently used)
        self.cache.move_to_end(key)
        self.hits += 1
        return value

    def set(self, key: str, value: Any):
        """Set value in cache"""
        # Remove oldest if at capacity
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)

        self.cache[key] = (value, time.time())

    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)

    def stats(self) -> Dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "size": self.size(),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "ttl": self.ttl,
        }


class CitationGraphService:
    """Citation graph service with caching and error handling"""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize service with database path"""
        self.db_path = db_path or config.CROSSREF_DB_PATH

        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        # Initialize cache
        self.cache = None
        if config.CACHE_ENABLED:
            self.cache = SimpleCache(
                max_size=config.CACHE_MAX_SIZE,
                ttl=config.CACHE_TTL_SECONDS
            )
            logger.info(f"Cache enabled: max_size={config.CACHE_MAX_SIZE}, ttl={config.CACHE_TTL_SECONDS}s")

        # Lazy load citation graph builder
        self._builder = None
        logger.info(f"Citation graph service initialized with database: {self.db_path}")

    @property
    def builder(self):
        """Lazy load citation graph builder"""
        if self._builder is None:
            try:
                from scitex.scholar.citation_graph import CitationGraphBuilder
                self._builder = CitationGraphBuilder(db_path=self.db_path)
                logger.info("Citation graph builder loaded successfully")
            except ImportError as e:
                logger.error(f"Failed to import CitationGraphBuilder: {e}")
                raise ImportError(
                    "scitex.scholar.citation_graph not found. "
                    "Install with: pip install -e ~/proj/scitex-code"
                )
        return self._builder

    def _make_cache_key(self, prefix: str, **kwargs) -> str:
        """Create cache key from parameters"""
        # Sort kwargs for consistent hashing
        sorted_params = sorted(kwargs.items())
        params_str = json.dumps(sorted_params, sort_keys=True)
        hash_str = hashlib.md5(params_str.encode()).hexdigest()[:12]
        return f"{prefix}:{hash_str}"

    def build_network(
        self,
        doi: str,
        top_n: int = None,
        weight_coupling: float = None,
        weight_cocitation: float = None,
        weight_direct: float = None,
        use_cache: bool = True,
    ) -> Dict:
        """
        Build citation network for a paper

        Args:
            doi: Seed paper DOI
            top_n: Number of related papers to include
            weight_coupling: Weight for bibliographic coupling
            weight_cocitation: Weight for co-citation
            weight_direct: Weight for direct citations
            use_cache: Whether to use cache

        Returns:
            Citation network dictionary
        """
        # Use defaults
        top_n = top_n or config.DEFAULT_TOP_N
        weight_coupling = weight_coupling or config.DEFAULT_WEIGHT_COUPLING
        weight_cocitation = weight_cocitation or config.DEFAULT_WEIGHT_COCITATION
        weight_direct = weight_direct or config.DEFAULT_WEIGHT_DIRECT

        # Validate parameters
        if top_n > config.MAX_TOP_N:
            top_n = config.MAX_TOP_N
            logger.warning(f"top_n capped at {config.MAX_TOP_N}")

        # Check cache
        cached = False
        if use_cache and self.cache:
            cache_key = self._make_cache_key(
                "network",
                doi=doi,
                top_n=top_n,
                w_c=weight_coupling,
                w_co=weight_cocitation,
                w_d=weight_direct,
            )
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for network: {doi}")
                cached_result["cached"] = True
                return cached_result

        # Build network
        try:
            logger.info(f"Building network for {doi} (top_n={top_n})")
            start_time = time.time()

            graph = self.builder.build(
                seed_doi=doi,
                top_n=top_n,
                weight_coupling=weight_coupling,
                weight_cocitation=weight_cocitation,
                weight_direct=weight_direct,
            )

            elapsed = time.time() - start_time
            logger.info(f"Network built in {elapsed:.2f}s: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

            # Format response
            result = {
                "seed": graph.seed_doi,
                "nodes": [
                    {
                        "doi": node.doi,
                        "title": node.title,
                        "year": node.year,
                        "authors": node.authors,
                        "similarity_score": round(node.similarity_score, 2),
                    }
                    for node in graph.nodes
                ],
                "edges": [
                    {
                        "source": edge.source,
                        "target": edge.target,
                        "edge_type": edge.edge_type,
                        "weight": edge.weight,
                    }
                    for edge in graph.edges
                ],
                "total_nodes": len(graph.nodes),
                "total_edges": len(graph.edges),
                "parameters": {
                    "top_n": top_n,
                    "weight_coupling": weight_coupling,
                    "weight_cocitation": weight_cocitation,
                    "weight_direct": weight_direct,
                },
                "cached": cached,
                "build_time_seconds": round(elapsed, 2),
            }

            # Cache result
            if use_cache and self.cache:
                self.cache.set(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Failed to build network for {doi}: {e}")
            raise

    def get_related_papers(
        self,
        doi: str,
        limit: int = 10,
        use_cache: bool = True,
    ) -> Dict:
        """
        Get related papers (lightweight version)

        Args:
            doi: Paper DOI
            limit: Maximum number of results
            use_cache: Whether to use cache

        Returns:
            Related papers list
        """
        # Build network and extract top papers
        network = self.build_network(doi=doi, top_n=limit, use_cache=use_cache)

        # Filter out seed paper and take top N
        related = [
            {
                "doi": node["doi"],
                "title": node["title"],
                "year": node["year"],
                "authors": node["authors"],
                "similarity_score": node["similarity_score"],
                "relationship": "similar",
            }
            for node in network["nodes"]
            if node["doi"] != doi
        ][:limit]

        return {
            "doi": doi,
            "related": related,
            "count": len(related),
            "cached": network["cached"],
        }

    def get_paper_summary(self, doi: str) -> Dict:
        """
        Get paper summary with citation counts

        Args:
            doi: Paper DOI

        Returns:
            Paper summary dictionary
        """
        try:
            db_access = self.builder.db

            # Get paper metadata
            paper = db_access.get_paper_by_doi(doi)
            if not paper:
                raise ValueError(f"Paper not found: {doi}")

            # Get citation counts
            references = db_access.get_references(doi)
            citations = db_access.get_citations(doi)

            return {
                "doi": paper.doi,
                "title": paper.title,
                "year": paper.year,
                "authors": paper.authors,
                "abstract": getattr(paper, "abstract", ""),
                "journal": getattr(paper, "journal", ""),
                "citation_count": len(citations),
                "reference_count": len(references),
            }

        except Exception as e:
            logger.error(f"Failed to get paper summary for {doi}: {e}")
            raise

    def health_check(self) -> Dict:
        """
        Health check for service

        Returns:
            Health status dictionary
        """
        try:
            # Test database access
            accessible = Path(self.db_path).exists()

            # Get cache stats
            cache_size = self.cache.size() if self.cache else 0

            return {
                "status": "healthy" if accessible else "degraded",
                "database_path": self.db_path,
                "database_accessible": accessible,
                "cache_enabled": config.CACHE_ENABLED,
                "cache_size": cache_size,
                "version": "1.0.0",
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "database_path": self.db_path,
                "database_accessible": False,
                "cache_enabled": False,
                "cache_size": 0,
                "version": "1.0.0",
                "error": str(e),
            }

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        if self.cache:
            return self.cache.stats()
        return {"enabled": False}

    def clear_cache(self):
        """Clear all cache"""
        if self.cache:
            self.cache.clear()
            logger.info("Cache cleared")


# Singleton instance
_service_instance = None


def get_service(db_path: Optional[str] = None) -> CitationGraphService:
    """Get or create service singleton"""
    global _service_instance

    if _service_instance is None:
        _service_instance = CitationGraphService(db_path=db_path)

    return _service_instance
