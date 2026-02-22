#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP tool data: scholar category."""

_R = "required"

SCHOLAR_TOOLS = {
    "category": "Scholar",
    "prefix": "scholar_*",
    "icon": "fa-graduation-cap",
    "tools": [
        {
            "name": "scholar_search_papers",
            "desc": "Search for scientific papers. Supports local library and external sources.",
            "params": [
                {"name": "query", "type": "str", "default": _R},
                {"name": "limit", "type": "int", "default": "20"},
                {"name": "year_min", "type": "int", "default": "None"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_fetch_papers",
            "desc": "Fetch papers to your library. Supports async mode which returns a job ID.",
            "params": [
                {"name": "papers", "type": "list[str]", "default": "None"},
                {"name": "bibtex_path", "type": "str", "default": "None"},
                {"name": "project", "type": "str", "default": "None"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_enrich_bibtex",
            "desc": "Enrich BibTeX entries with metadata: DOIs, abstracts, citation counts.",
            "params": [
                {"name": "bibtex_path", "type": "str", "default": _R},
                {"name": "output_path", "type": "str", "default": "None"},
                {"name": "add_abstracts", "type": "bool", "default": "True"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_resolve_dois",
            "desc": "Resolve DOIs from paper titles using Crossref API. Supports resumable batch.",
            "params": [
                {"name": "titles", "type": "list[str]", "default": "None"},
                {"name": "bibtex_path", "type": "str", "default": "None"},
                {"name": "project", "type": "str", "default": "None"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_download_pdfs_batch",
            "desc": "Download PDFs for multiple papers with progress tracking.",
            "params": [
                {"name": "dois", "type": "list[str]", "default": "None"},
                {"name": "bibtex_path", "type": "str", "default": "None"},
                {"name": "project", "type": "str", "default": "None"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_parse_pdf_content",
            "desc": "Parse PDF content to extract text, sections (IMRaD), tables, images.",
            "params": [
                {"name": "pdf_path", "type": "str", "default": "None"},
                {"name": "doi", "type": "str", "default": "None"},
                {"name": "project", "type": "str", "default": "None"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_parse_bibtex",
            "desc": "Parse a BibTeX file and return paper objects.",
            "params": [
                {"name": "bibtex_path", "type": "str", "default": _R},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_export_papers",
            "desc": "Export papers to various formats (BibTeX, RIS, JSON, CSV).",
            "params": [
                {"name": "output_path", "type": "str", "default": _R},
                {"name": "project", "type": "str", "default": "None"},
                {"name": "format", "type": "str", "default": "'bibtex'"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_get_library_status",
            "desc": "Get status of the paper library: download progress, missing PDFs.",
            "params": [
                {"name": "project", "type": "str", "default": "None"},
                {"name": "include_details", "type": "bool", "default": "False"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_validate_pdfs",
            "desc": "Validate PDF files in library for completeness and readability.",
            "params": [
                {"name": "project", "type": "str", "default": "None"},
                {"name": "pdf_paths", "type": "list[str]", "default": "None"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_create_project",
            "desc": "Create a new scholar project for organizing papers.",
            "params": [
                {"name": "project_name", "type": "str", "default": _R},
                {"name": "description", "type": "str", "default": "None"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_list_projects",
            "desc": "List all scholar projects in the library.",
            "params": [],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_add_papers_to_project",
            "desc": "Add papers to a project by DOI or from BibTeX file.",
            "params": [
                {"name": "project", "type": "str", "default": _R},
                {"name": "dois", "type": "list[str]", "default": "None"},
                {"name": "bibtex_path", "type": "str", "default": "None"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_authenticate",
            "desc": "Start SSO login for institutional access (OpenAthens, Shibboleth).",
            "params": [
                {"name": "method", "type": "str", "default": _R},
                {"name": "institution", "type": "str", "default": "None"},
                {"name": "force", "type": "bool", "default": "False"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_check_auth_status",
            "desc": "Check current authentication status without starting login.",
            "params": [
                {"name": "method", "type": "str", "default": "'openathens'"},
                {"name": "verify_live", "type": "bool", "default": "False"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_logout",
            "desc": "Logout from institutional authentication and clear session cache.",
            "params": [
                {"name": "method", "type": "str", "default": "'openathens'"},
                {"name": "clear_cache", "type": "bool", "default": "True"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_resolve_openurls",
            "desc": "Resolve publisher URLs via OpenURL resolver for institutional access.",
            "params": [
                {"name": "dois", "type": "list[str]", "default": _R},
                {"name": "resolver_url", "type": "str", "default": "None"},
                {"name": "resume", "type": "bool", "default": "True"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_fetch_papers",
            "desc": "Fetch papers to your library; async mode returns job_id.",
            "params": [
                {"name": "papers", "type": "list[str]", "default": "None"},
                {"name": "bibtex_path", "type": "str", "default": "None"},
                {"name": "project", "type": "str", "default": "None"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_list_jobs",
            "desc": "List all background jobs with their status.",
            "params": [
                {"name": "status", "type": "str", "default": "None"},
                {"name": "limit", "type": "int", "default": "20"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_get_job_status",
            "desc": "Get detailed status of a specific job including progress.",
            "params": [
                {"name": "job_id", "type": "str", "default": _R},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_start_job",
            "desc": "Start a pending job that was submitted with async mode.",
            "params": [
                {"name": "job_id", "type": "str", "default": _R},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_cancel_job",
            "desc": "Cancel a running or pending job.",
            "params": [
                {"name": "job_id", "type": "str", "default": _R},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "scholar_get_job_result",
            "desc": "Get the result of a completed job.",
            "params": [
                {"name": "job_id", "type": "str", "default": _R},
            ],
            "returns": "str (JSON)",
        },
    ],
}

# EOF
