#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar API endpoint definitions."""

SCHOLAR_CATEGORY = {
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
}
