"""
Citation Graph Service

Thin Django wrapper around scitex.scholar.citation_graph.
Adds Django cache layer on top of the core module.

All detection logic (DB vs HTTP) lives in crossref_local.Config
and is used by CitationGraphBuilder automatically.
"""

import hashlib
import logging
from typing import Dict, List, Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)


class CitationGraphService:
    """
    Django service wrapping CitationGraphBuilder with caching.

    Detection of DB vs HTTP mode is handled entirely by
    crossref_local.Config (via scitex.scholar.citation_graph).
    """

    def __init__(self):
        """Initialize service — delegates detection to scitex."""
        from scitex.scholar.citation_graph import CitationGraphBuilder

        self.builder = CitationGraphBuilder()  # auto-detects via Config
        logger.info("Citation graph service initialized")

    def _cache_key(self, prefix: str, doi: str, **kwargs) -> str:
        """Create cache key from parameters."""
        key_parts = [prefix, doi.lower()]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        key_str = ":".join(key_parts)
        return f"citation_graph:{hashlib.md5(key_str.encode()).hexdigest()}"

    def get_paper_summary(self, doi: str, use_cache: bool = True) -> Optional[Dict]:
        """Get summary information for a paper."""
        cache_key = self._cache_key("summary", doi)

        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                cached["cached"] = True
                return cached

        summary = self.builder.get_paper_summary(doi)
        if summary:
            cache.set(cache_key, summary, 3600)
            summary["cached"] = False
            return summary
        return None

    def build_network(
        self,
        doi: str,
        top_n: int = 20,
        weight_coupling: float = 2.0,
        weight_cocitation: float = 2.0,
        weight_direct: float = 1.0,
        use_cache: bool = True,
    ) -> Dict:
        """Build citation network graph for a paper."""
        cache_key = self._cache_key(
            "network",
            doi,
            top_n=top_n,
            wc=weight_coupling,
            wco=weight_cocitation,
            wd=weight_direct,
        )

        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                cached["metadata"]["cached"] = True
                return cached

        graph = self.builder.build(
            seed_doi=doi,
            top_n=top_n,
            weight_coupling=weight_coupling,
            weight_cocitation=weight_cocitation,
            weight_direct=weight_direct,
        )

        result = graph.to_dict()
        result["metadata"]["cached"] = False
        cache.set(cache_key, result, 3600)

        logger.info(
            f"Built network for {doi}: "
            f"{len(result['nodes'])} nodes, {len(result['edges'])} edges"
        )
        return result

    def _cache_key_multi(self, prefix: str, dois: List[str], **kwargs) -> str:
        """Create cache key from multiple DOIs."""
        key_parts = [prefix] + sorted(d.lower() for d in dois)
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        key_str = ":".join(key_parts)
        return f"citation_graph:{hashlib.md5(key_str.encode()).hexdigest()}"

    def build_network_from_dois(
        self,
        dois: List[str],
        num_related_per_doi: int = 20,
        use_cache: bool = True,
    ) -> Dict:
        """Build citation network from multiple seed DOIs."""
        cache_key = self._cache_key_multi(
            "network_multi", dois, nrpd=num_related_per_doi
        )

        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                cached["metadata"]["cached"] = True
                return cached

        graph = self.builder.build_from_dois(
            dois=dois,
            num_related_per_doi=num_related_per_doi,
        )

        result = graph.to_dict()
        result["metadata"]["cached"] = False
        cache.set(cache_key, result, 3600)

        logger.info(
            f"Built multi-seed network for {len(dois)} DOIs: "
            f"{len(result['nodes'])} nodes, {len(result['edges'])} edges"
        )
        return result

    def build_network_from_query(
        self,
        query: str,
        num_related_per_doi: int = 20,
        search_limit: int = 10,
        use_cache: bool = True,
    ) -> Dict:
        """Build citation network from a text query. Delegates to scitex."""
        cache_key = self._cache_key(
            "network_query",
            query.lower().strip(),
            nrpd=num_related_per_doi,
            sl=search_limit,
        )

        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                cached["metadata"]["cached"] = True
                return cached

        graph = self.builder.build_from_query(
            query=query,
            num_related_per_doi=num_related_per_doi,
            search_limit=search_limit,
        )

        result = graph.to_dict()
        result["metadata"]["cached"] = False
        cache.set(cache_key, result, 3600)

        logger.info(
            f"Built query network for '{query}': "
            f"{len(result['nodes'])} nodes, {len(result['edges'])} edges"
        )
        return result

    def get_related_papers(
        self, doi: str, limit: int = 10, use_cache: bool = True
    ) -> List[Dict]:
        """Get related papers (lightweight: just nodes, no graph)."""
        network = self.build_network(doi=doi, top_n=limit, use_cache=use_cache)
        nodes = sorted(
            network["nodes"],
            key=lambda n: n.get("similarity_score", 0),
            reverse=True,
        )
        return [n for n in nodes if n["id"].lower() != doi.lower()][:limit]

    def health_check(self) -> Dict:
        """Check service health (cached 30s to prevent floods)."""
        cache_key = "citation_graph:health_status"
        cached_status = cache.get(cache_key)
        if cached_status:
            cached_status["cached"] = True
            return cached_status

        try:
            test_doi = "10.1038/s41586-020-2008-3"
            summary = self.get_paper_summary(test_doi, use_cache=False)

            result = {
                "status": "healthy" if summary else "degraded",
                "mode": "http" if self.builder.db_path is None else "db",
                "cached": False,
            }
            if not summary:
                result["warning"] = "Test DOI not found"

            cache.set(cache_key, result, 30)
            return result

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            result = {
                "status": "unhealthy",
                "error": str(e),
                "cached": False,
            }
            cache.set(cache_key, result, 10)
            return result


def get_citation_graph_service() -> CitationGraphService:
    """
    Get citation graph service instance.

    All backend detection (DB vs HTTP) is handled by
    crossref_local.Config inside CitationGraphBuilder.
    """
    return CitationGraphService()
