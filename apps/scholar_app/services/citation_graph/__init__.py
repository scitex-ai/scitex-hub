"""
Citation Graph Service Layer

Provides business logic for citation network analysis using the
scitex.scholar.citation_graph module.
"""

from .service import CitationGraphService, get_citation_graph_service

__all__ = ["CitationGraphService", "get_citation_graph_service"]
