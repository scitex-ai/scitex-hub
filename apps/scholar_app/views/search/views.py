#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/search/views.py
# Refactored: Thin wrapper that imports from modular sub-files
# ----------------------------------------
"""
This file serves as a compatibility layer after refactoring.
All functions are now organized into focused modules:
- search_core.py: Main search views
- search_helpers.py: Filter and helper functions
- search_engines.py: External API search implementations
- api_search.py: API endpoints for progressive search
- saved_searches.py: Saved search management
- library_operations.py: Library save/bulk operations
- citation_export_core.py: Citation generation
- storage.py: Database storage functions
- project_views.py: Project-specific views
"""

# Import all functions from modular files to maintain backward compatibility
from .api_search import (
    api_search_arxiv,
    api_search_biorxiv,
    api_search_crossref,
    api_search_crossref_local,
    api_search_doaj,
    api_search_openalex,
    api_search_openalex_local,
    api_search_plos,
    api_search_pmc,
    api_search_pubmed,
    api_search_semantic,
    api_search_syntax_help,
    api_search_unified,
)
from .citation_export_core import (
    export_citation,
    generate_bibtex,
    generate_citation,
    generate_citation_key,
    generate_endnote,
    generate_ris,
    get_file_extension,
    sanitize_filename,
)
from .citations import (
    get_impact_factor_instance,
    get_journal_impact_factor,
    get_pubmed_citations,
    is_open_access_journal,
    validate_citation_count,
)
from .engines import (
    search_arxiv,
    search_arxiv_real,
    search_biorxiv,
    search_doaj,
    search_papers_online,
    search_plos,
    search_pubmed,
    search_pubmed_central,
    search_pubmed_central_fast,
    search_pubmed_fast,
    search_semantic_scholar,
    search_with_scitex_scholar,
)
from .library_operations import (
    get_citation,
    mock_get_citation,
    mock_save_paper,
    save_paper,
    save_papers_bulk,
    upload_file,
)

# Re-export from other modules that were previously in this file
from .page_views import (
    bibtex_enrichment_view,
    features,
    index,
    literature_search_view,
    personal_library,
    pricing,
    scholar_bibtex,
    scholar_graph,
    scholar_search,
    scholar_unified,
    simple_search,
)
from .preferences import (
    get_user_preferences,
    save_source_preferences,
    save_user_preferences,
)
from .project_views import (
    project_library,
)
from .recommendations import (
    paper_recommendations,
    user_recommendations,
)
from .saved_searches import (
    delete_saved_search,
    get_saved_searches,
    run_saved_search,
    save_search,
)
from .search_core import (
    simple_search_with_tab,
)
from .search_helpers import (
    apply_advanced_filters,
    extract_search_filters,
    get_paper_authors,
    search_database_papers,
)
from .storage import (
    _create_paper_authors,
    store_search_result,
)

__all__ = [
    # Search Core
    "simple_search",
    "simple_search_with_tab",
    # Search Helpers
    "extract_search_filters",
    "search_database_papers",
    "apply_advanced_filters",
    "get_paper_authors",
    # Search Engines
    "search_papers_online",
    "search_with_scitex_scholar",
    "search_arxiv_real",
    "search_pubmed_central_fast",
    "search_pubmed_fast",
    "search_arxiv",
    "search_pubmed",
    "search_pubmed_central",
    "search_doaj",
    "search_biorxiv",
    "search_plos",
    "search_semantic_scholar",
    # API Search
    "api_search_arxiv",
    "api_search_pubmed",
    "api_search_semantic",
    "api_search_pmc",
    "api_search_doaj",
    "api_search_biorxiv",
    "api_search_plos",
    "api_search_crossref",
    "api_search_crossref_local",
    "api_search_openalex",
    "api_search_openalex_local",
    "api_search_unified",
    "api_search_syntax_help",
    # Saved Searches
    "save_search",
    "get_saved_searches",
    "delete_saved_search",
    "run_saved_search",
    # Library Operations
    "save_paper",
    "save_papers_bulk",
    "upload_file",
    "get_citation",
    "mock_save_paper",
    "mock_get_citation",
    # Citation Export
    "export_citation",
    "generate_citation",
    "generate_citation_key",
    "generate_bibtex",
    "generate_endnote",
    "generate_ris",
    "sanitize_filename",
    "get_file_extension",
    # Storage
    "store_search_result",
    "_create_paper_authors",
    # Project Views
    "project_library",
    # Page Views
    "index",
    "scholar_bibtex",
    "scholar_search",
    "scholar_graph",
    "scholar_unified",
    "bibtex_enrichment_view",
    "literature_search_view",
    "features",
    "pricing",
    "personal_library",
    # Preferences
    "get_user_preferences",
    "save_user_preferences",
    "save_source_preferences",
    # Citations
    "get_impact_factor_instance",
    "get_journal_impact_factor",
    "is_open_access_journal",
    "get_pubmed_citations",
    "validate_citation_count",
    # Recommendations
    "paper_recommendations",
    "user_recommendations",
]
