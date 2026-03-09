#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public API endpoint definitions."""

PUBLIC_CATEGORY = {
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
}
