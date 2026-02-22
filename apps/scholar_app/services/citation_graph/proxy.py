"""
Citation Graph Proxy Service

Proxies requests to NAS when local database is not available.
Used in development environment to access production database.

Configuration:
    Set SCITEX_SCHOLAR_CITATION_GRAPH_PROXY_URL in .env.dev to specify proxy target.
    (Falls back to legacy SCITEX_CITATION_GRAPH_PROXY_URL)
    Default: https://scitex.ai
"""

import logging
import os
from typing import Dict, List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_proxy_url() -> str:
    """Get proxy URL from environment or settings."""
    # 1. Try environment variable (set in .env.dev)
    # Support both new (SCITEX_SCHOLAR_*) and legacy (SCITEX_*) names
    url = os.environ.get("SCITEX_SCHOLAR_CITATION_GRAPH_PROXY_URL") or os.environ.get(
        "SCITEX_CITATION_GRAPH_PROXY_URL"
    )
    if url:
        return url

    # 2. Try Django settings
    url = getattr(settings, "CITATION_GRAPH_PROXY_URL", None)
    if url:
        return url

    # 3. Default fallback
    return "https://scitex.ai"


class CitationGraphProxyService:
    """
    Proxy service that forwards citation graph requests to NAS.

    Used when local CrossRef database is not available (dev environment).
    Configure via SCITEX_SCHOLAR_CITATION_GRAPH_PROXY_URL in .env.dev
    """

    def __init__(self, base_url: str = None):
        """Initialize proxy with NAS URL from environment."""
        self.base_url = base_url or _get_proxy_url()
        self.timeout = 60  # Long timeout for network building
        logger.info(f"Citation graph proxy initialized: {self.base_url}")

    def _make_request(self, endpoint: str, params: dict) -> dict:
        """Make GET request to NAS API."""
        url = f"{self.base_url}/api/scholar/citation-graph/{endpoint}/"
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Proxy request failed: {e}")
            raise

    def get_paper_summary(self, doi: str, use_cache: bool = True) -> Optional[Dict]:
        """Get paper summary via NAS proxy."""
        params = {"doi": doi}
        if not use_cache:
            params["no_cache"] = "true"
        try:
            result = self._make_request("paper", params)
            result["proxied"] = True
            return result
        except Exception as e:
            logger.error(f"Proxy error getting paper summary: {e}")
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
        """Build network via NAS proxy."""
        params = {
            "doi": doi,
            "top_n": top_n,
            "weight_coupling": weight_coupling,
            "weight_cocitation": weight_cocitation,
            "weight_direct": weight_direct,
        }
        if not use_cache:
            params["no_cache"] = "true"

        result = self._make_request("network", params)
        result["metadata"]["proxied"] = True
        return result

    def build_network_from_dois(
        self,
        dois: List[str],
        num_related_per_doi: int = 20,
        use_cache: bool = True,
    ) -> Dict:
        """Build multi-DOI network via NAS proxy."""
        params = {
            "dois": ",".join(dois),
            "num_related_per_doi": num_related_per_doi,
        }
        if not use_cache:
            params["no_cache"] = "true"

        result = self._make_request("network/multi", params)
        result["metadata"]["proxied"] = True
        return result

    def build_network_from_query(
        self,
        query: str,
        num_related_per_doi: int = 20,
        search_limit: int = 10,
        use_cache: bool = True,
    ) -> Dict:
        """Build query network via NAS proxy."""
        params = {
            "q": query,
            "num_related_per_doi": num_related_per_doi,
            "search_limit": search_limit,
        }
        if not use_cache:
            params["no_cache"] = "true"

        result = self._make_request("network/query", params)
        result["metadata"]["proxied"] = True
        return result

    def get_related_papers(
        self, doi: str, limit: int = 10, use_cache: bool = True
    ) -> List[Dict]:
        """Get related papers via NAS proxy."""
        params = {"doi": doi, "limit": limit}
        if not use_cache:
            params["no_cache"] = "true"

        result = self._make_request("related", params)
        return result.get("related", [])

    def health_check(self) -> Dict:
        """Check NAS service health with short timeout."""
        try:
            # Use short timeout for health checks (not the 60s default)
            url = f"{self.base_url}/api/scholar/citation-graph/health/"
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            result = response.json()
            result["mode"] = "proxy"
            result["proxy_target"] = self.base_url
            return result
        except Exception as e:
            return {
                "status": "unhealthy",
                "mode": "proxy",
                "proxy_target": self.base_url,
                "error": str(e),
            }
