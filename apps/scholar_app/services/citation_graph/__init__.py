"""
Citation Graph Service Layer

Thin Django wrapper around scitex.scholar.citation_graph.
Backend detection (DB vs HTTP) handled by crossref_local.Config.
"""

from .service import CitationGraphService, get_citation_graph_service

__all__ = [
    "CitationGraphService",
    "get_citation_graph_service",
]
