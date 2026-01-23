#!/usr/bin/env python3
"""Pydantic models for Citation Graph API"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class PaperNode(BaseModel):
    """Paper node in citation graph"""
    doi: str = Field(..., description="Paper DOI")
    title: str = Field(default="", description="Paper title")
    year: Optional[int] = Field(None, description="Publication year")
    authors: List[str] = Field(default_factory=list, description="Author names")
    similarity_score: float = Field(default=0.0, description="Similarity score to seed paper")

    class Config:
        json_schema_extra = {
            "example": {
                "doi": "10.1038/s41586-020-2008-3",
                "title": "A new coronavirus associated with human respiratory disease in China",
                "year": 2020,
                "authors": ["Fan Wu", "Su Zhao", "Bin Yu"],
                "similarity_score": 95.5
            }
        }


class CitationEdge(BaseModel):
    """Citation edge between papers"""
    source: str = Field(..., description="Source paper DOI")
    target: str = Field(..., description="Target paper DOI")
    edge_type: str = Field(default="cites", description="Edge type (cites, cited_by, similar)")
    weight: float = Field(default=1.0, description="Edge weight")

    class Config:
        json_schema_extra = {
            "example": {
                "source": "10.1038/s41586-020-2008-3",
                "target": "10.1016/j.cell.2020.02.052",
                "edge_type": "cites",
                "weight": 1.0
            }
        }


class CitationGraphResponse(BaseModel):
    """Citation network response"""
    seed: str = Field(..., description="Seed paper DOI")
    nodes: List[PaperNode] = Field(..., description="Papers in the network")
    edges: List[CitationEdge] = Field(..., description="Citation relationships")
    total_nodes: int = Field(..., description="Total number of nodes")
    total_edges: int = Field(..., description="Total number of edges")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Query parameters used")
    cached: bool = Field(default=False, description="Whether result was cached")

    class Config:
        json_schema_extra = {
            "example": {
                "seed": "10.1038/s41586-020-2008-3",
                "nodes": [
                    {
                        "doi": "10.1038/s41586-020-2008-3",
                        "title": "A new coronavirus...",
                        "year": 2020,
                        "authors": ["Fan Wu", "Su Zhao"],
                        "similarity_score": 100.0
                    }
                ],
                "edges": [
                    {
                        "source": "10.1038/s41586-020-2008-3",
                        "target": "10.1016/j.cell.2020.02.052",
                        "edge_type": "cites",
                        "weight": 1.0
                    }
                ],
                "total_nodes": 21,
                "total_edges": 45,
                "parameters": {"top_n": 20, "weights": [2.0, 2.0, 1.0]},
                "cached": False
            }
        }


class RelatedPaper(BaseModel):
    """Related paper summary"""
    doi: str
    title: str
    year: Optional[int] = None
    authors: List[str] = Field(default_factory=list)
    similarity_score: float
    relationship: str = Field(default="similar", description="Relationship type")


class RelatedPapersResponse(BaseModel):
    """Related papers response (lightweight)"""
    doi: str = Field(..., description="Query paper DOI")
    related: List[RelatedPaper] = Field(..., description="Related papers")
    count: int = Field(..., description="Number of results")
    cached: bool = Field(default=False, description="Whether result was cached")


class PaperSummary(BaseModel):
    """Paper summary with citation counts"""
    doi: str
    title: str
    year: Optional[int] = None
    authors: List[str] = Field(default_factory=list)
    abstract: str = Field(default="")
    journal: str = Field(default="")
    citation_count: int = Field(default=0, description="Number of papers citing this one")
    reference_count: int = Field(default=0, description="Number of papers this one cites")

    class Config:
        json_schema_extra = {
            "example": {
                "doi": "10.1038/s41586-020-2008-3",
                "title": "A new coronavirus associated with human respiratory disease in China",
                "year": 2020,
                "authors": ["Fan Wu", "Su Zhao", "Bin Yu"],
                "abstract": "Emerging infectious diseases...",
                "journal": "Nature",
                "citation_count": 12500,
                "reference_count": 42
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    database_path: str = Field(..., description="Database path")
    database_accessible: bool = Field(..., description="Database accessibility")
    cache_enabled: bool = Field(..., description="Cache status")
    cache_size: int = Field(default=0, description="Current cache size")
    version: str = Field(default="1.0.0", description="API version")


class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error details")
    doi: Optional[str] = Field(None, description="Related DOI if applicable")
