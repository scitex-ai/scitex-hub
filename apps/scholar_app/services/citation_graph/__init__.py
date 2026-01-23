"""
Citation Graph Service Layer

Provides business logic for citation network analysis using the
scitex.scholar.citation_graph module.

In dev environment (no local database), automatically proxies to NAS.
"""

from .service import CitationGraphService, get_citation_graph_service
from .proxy import CitationGraphProxyService

__all__ = [
    "CitationGraphService",
    "CitationGraphProxyService",
    "get_citation_graph_service"
]
