#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API Registry - Single Source of Truth for all SciTeX APIs.

This registry defines all exposed APIs. Documentation is generated
programmatically from this registry to ensure consistency.
"""

from __future__ import annotations

# API Categories and Endpoints
API_REGISTRY = {
    "public": {
        "name": "Public API",
        "description": "No authentication required. Rate-limited.",
        "base_path": "/api/v1",
        "auth_required": False,
        "endpoints": [
            {
                "method": "GET",
                "path": "/scholar/search/",
                "name": "Public Search",
                "description": "Search across academic databases. Rate-limited to 10 req/min for anonymous users.",
                "params": [
                    {
                        "name": "q",
                        "type": "string",
                        "required": True,
                        "desc": "Search query",
                    },
                    {
                        "name": "limit",
                        "type": "int",
                        "required": False,
                        "desc": "Max results per source (default: 20, max: 100)",
                    },
                    {
                        "name": "format",
                        "type": "string",
                        "required": False,
                        "desc": "Response format: json, bibtex, csv, text",
                    },
                    {
                        "name": "sources",
                        "type": "string",
                        "required": False,
                        "desc": "Comma-separated: pubmed, arxiv, semantic, crossref, openalex",
                    },
                ],
                "response_fields": [
                    {"name": "title", "type": "string", "desc": "Paper title"},
                    {
                        "name": "authors",
                        "type": "string",
                        "desc": "Comma-separated authors",
                    },
                    {"name": "journal", "type": "string", "desc": "Journal name"},
                    {"name": "year", "type": "string", "desc": "Publication year"},
                    {"name": "doi", "type": "string", "desc": "DOI"},
                    {"name": "pmid", "type": "string", "desc": "PubMed ID"},
                    {"name": "arxiv_id", "type": "string", "desc": "arXiv ID"},
                    {"name": "citations", "type": "int", "desc": "Citation count"},
                    {"name": "impact_factor", "type": "float", "desc": "Journal IF"},
                    {"name": "is_open_access", "type": "bool", "desc": "Open access?"},
                    {"name": "abstract", "type": "string", "desc": "Abstract"},
                    {"name": "url", "type": "string", "desc": "Paper URL"},
                    {"name": "source", "type": "string", "desc": "Data source"},
                ],
                "response_example": {
                    "status": "success",
                    "query": "epilepsy EEG",
                    "total_results": 42,
                    "results": [
                        {
                            "title": "Deep learning for epileptic seizure detection",
                            "authors": "Smith J, Lee K, Wang M",
                            "journal": "Nature Neuroscience",
                            "year": "2024",
                            "doi": "10.1038/s41593-024-01234-5",
                            "pmid": "38123456",
                            "citations": 128,
                            "impact_factor": 28.771,
                            "is_open_access": True,
                            "abstract": "We present a novel deep learning...",
                            "url": "https://doi.org/10.1038/s41593-024-01234-5",
                            "source": "pubmed",
                        }
                    ],
                },
            },
            {
                "method": "GET",
                "path": "/scholar/info/",
                "name": "API Info",
                "description": "API documentation and rate limit status",
                "params": [],
            },
        ],
    },
    "scholar": {
        "name": "Scholar API",
        "description": "Academic paper search and management. Higher rate limits (100/min) and additional features like PDF download.",
        "base_path": "/scholar/api",
        "auth_required": True,
        "endpoints": [
            {
                "method": "GET",
                "path": "/search/",
                "name": "Search Papers",
                "description": "Search papers with authentication. Higher limits and workspace integration.",
                "params": [
                    {
                        "name": "q",
                        "type": "string",
                        "required": True,
                        "desc": "Search query",
                    },
                    {
                        "name": "limit",
                        "type": "int",
                        "required": False,
                        "desc": "Max results",
                    },
                ],
            },
            {
                "method": "GET",
                "path": "/crossref/search/",
                "name": "CrossRef Search",
                "description": "Search CrossRef database",
                "params": [
                    {
                        "name": "q",
                        "type": "string",
                        "required": True,
                        "desc": "Search query",
                    },
                ],
            },
            {
                "method": "GET",
                "path": "/crossref/health/",
                "name": "CrossRef Health",
                "description": "Check CrossRef service status",
                "params": [],
            },
            {
                "method": "GET",
                "path": "/crossref/citations/",
                "name": "Get Citations",
                "description": "Get citations for a DOI",
                "params": [
                    {
                        "name": "doi",
                        "type": "string",
                        "required": True,
                        "desc": "DOI to lookup",
                    },
                ],
            },
            {
                "method": "POST",
                "path": "/pdf/download/",
                "name": "Download PDF",
                "description": "Request PDF download for a paper",
                "params": [
                    {
                        "name": "doi",
                        "type": "string",
                        "required": True,
                        "desc": "Paper DOI",
                    },
                ],
            },
            {
                "method": "GET",
                "path": "/pdf/status/",
                "name": "PDF Status",
                "description": "Check PDF download status",
                "params": [
                    {
                        "name": "task_id",
                        "type": "string",
                        "required": True,
                        "desc": "Task ID",
                    },
                ],
            },
        ],
    },
    "writer": {
        "name": "Writer API",
        "description": "LaTeX manuscript compilation",
        "base_path": "/writer/api",
        "auth_required": True,
        "endpoints": [
            {
                "method": "POST",
                "path": "/compile/",
                "name": "Compile Manuscript",
                "description": "Compile LaTeX project to PDF",
                "params": [
                    {
                        "name": "project_id",
                        "type": "uuid",
                        "required": True,
                        "desc": "Project ID",
                    },
                    {
                        "name": "output_format",
                        "type": "string",
                        "required": False,
                        "desc": "Output: pdf, html",
                    },
                ],
            },
            {
                "method": "GET",
                "path": "/sections/",
                "name": "List Sections",
                "description": "Get manuscript sections",
                "params": [
                    {
                        "name": "project_id",
                        "type": "uuid",
                        "required": True,
                        "desc": "Project ID",
                    },
                ],
            },
        ],
    },
    "project": {
        "name": "Project API",
        "description": "Project file and Git operations",
        "base_path": "/project/api",
        "auth_required": True,
        "endpoints": [
            {
                "method": "GET",
                "path": "/files/",
                "name": "List Files",
                "description": "List project files",
                "params": [
                    {
                        "name": "project_id",
                        "type": "uuid",
                        "required": True,
                        "desc": "Project ID",
                    },
                ],
            },
            {
                "method": "POST",
                "path": "/git/commit/",
                "name": "Git Commit",
                "description": "Commit changes to project",
                "params": [
                    {
                        "name": "project_id",
                        "type": "uuid",
                        "required": True,
                        "desc": "Project ID",
                    },
                    {
                        "name": "message",
                        "type": "string",
                        "required": True,
                        "desc": "Commit message",
                    },
                ],
            },
        ],
    },
}

# Rate Limits
RATE_LIMITS = {
    "anonymous": {"limit": 10, "window": "minute", "note": "Public API only"},
    "api_key": {"limit": 100, "window": "minute", "note": "All endpoints"},
    "campaign": {"limit": 100, "window": "minute", "note": "Alpha testing"},
}

# Error Codes
ERROR_CODES = {
    200: "Success",
    400: "Bad Request - Invalid parameters",
    401: "Unauthorized - Missing/invalid auth",
    403: "Forbidden - Insufficient permissions",
    404: "Not Found - Resource doesn't exist",
    429: "Too Many Requests - Rate limit exceeded",
    500: "Server Error - Internal error",
}


def get_all_endpoints():
    """Get flat list of all endpoints."""
    endpoints = []
    for category, info in API_REGISTRY.items():
        for ep in info["endpoints"]:
            endpoints.append(
                {
                    "category": category,
                    "category_name": info["name"],
                    "base_path": info["base_path"],
                    "auth_required": info["auth_required"],
                    **ep,
                }
            )
    return endpoints


def get_endpoints_by_category(category: str):
    """Get endpoints for a specific category."""
    if category not in API_REGISTRY:
        return []
    info = API_REGISTRY[category]
    return [
        {"base_path": info["base_path"], "auth_required": info["auth_required"], **ep}
        for ep in info["endpoints"]
    ]
