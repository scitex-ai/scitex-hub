#!/usr/bin/env python3
"""Pydantic models for CrossRef Local API"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class PaperMetadata(BaseModel):
    """Paper metadata response"""
    doi: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    issn: Optional[str] = None
    publisher: Optional[str] = None
    abstract: Optional[str] = None
    citation_count: Optional[int] = 0
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    url: Optional[str] = None

    class Config:
        extra = "allow"


class CitationEdge(BaseModel):
    """Citation graph edge"""
    source: str  # DOI of citing paper
    target: str  # DOI of cited paper
    type: str = "cites"


class CitationNode(BaseModel):
    """Citation graph node"""
    doi: str
    title: Optional[str] = None
    year: Optional[int] = None
    authors: Optional[List[str]] = None
    citation_count: Optional[int] = 0


class CitationGraph(BaseModel):
    """Citation graph response"""
    center_doi: str
    nodes: List[CitationNode]
    edges: List[CitationEdge]
    total_nodes: int
    total_edges: int


class JournalMetrics(BaseModel):
    """Journal metrics response"""
    issn: Optional[str] = None
    name: str
    publisher: Optional[str] = None
    total_papers: Optional[int] = None
    year_range: Optional[List[int]] = None


class SearchResponse(BaseModel):
    """Search results response"""
    query: Dict[str, Any]
    results: List[PaperMetadata]
    total: int
    returned: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    database_connected: bool
    database_path: str
    total_papers: Optional[int] = None
    database_size_mb: Optional[float] = None
    has_citations: Optional[bool] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class StatsResponse(BaseModel):
    """Database statistics response"""
    total_papers: int
    database_size_mb: float
    year_range: Optional[List[int]] = None
    total_journals: Optional[int] = None
    total_citations: Optional[int] = None
    tables: List[str]
    indices: List[str]


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
