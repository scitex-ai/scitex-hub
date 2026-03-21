#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scholar App Views Package

Feature-based organization:
- search: Paper search and discovery
- library: Personal library management
- bibtex: BibTeX import and enrichment
- repository: Paper repository browsing
- annotation: Paper annotation and collaboration
- export: Citation export functionality
- workspace: User workspace management
- trending: Trending papers and research analytics
"""

# Import search views
# Import annotation views
from .annotation.views import (
    api_collaboration_groups,
    api_create_annotation,
    api_delete_annotation,
    api_paper_annotations,
    api_update_annotation,
    api_vote_annotation,
    paper_annotations,
    paper_recommendations,
    user_recommendations,
)

# Import bibtex views
from .bibtex import (
    bibtex_cancel_job,
    bibtex_download_enriched,
    bibtex_enrichment,
    bibtex_get_urls,
    bibtex_job_detail,
    bibtex_job_diff,
    bibtex_job_status,
    bibtex_resource_status,
    bibtex_upload,
)

# Import export views
from .export.views import (
    export_bibtex,
    export_bulk_citations,
    export_collection,
    export_csv,
    export_endnote,
    export_ris,
)

# Import library views
from .library.views import (
    api_create_collection,
    api_library_collections,
    api_library_papers,
    api_remove_library_paper,
    api_update_library_paper,
    personal_library,
)

# Import repository views
from .repository import (
    DatasetViewSet,
    RepositoryConnectionViewSet,
    RepositoryViewSet,
    create_repository_connection,
    list_repositories,
    sync_status,
    user_repository_stats,
)
from .search.views import (
    api_search_arxiv,
    api_search_biorxiv,
    api_search_doaj,
    api_search_plos,
    api_search_pmc,
    api_search_pubmed,
    api_search_semantic,
    delete_saved_search,
    get_citation,
    get_saved_searches,
    get_user_preferences,
    index,
    mock_get_citation,
    mock_save_paper,
    run_saved_search,
    save_paper,
    save_papers_bulk,
    save_search,
    save_source_preferences,
    save_user_preferences,
    simple_search,
    upload_file,
)

# Import trending views
from .trending.views import (
    api_research_analytics,
    api_trending_authors,
    api_trending_papers,
    api_trending_topics,
    research_trends,
)

# Import workspace views (API key management)
from .workspace.api_key_views import (
    api_key_management,
    api_usage_stats,
    test_api_key,
)

# Import workspace views
from .workspace.views import (
    user_default_workspace,
)

__all__ = [
    # Search views
    "index",
    "simple_search",
    "get_citation",
    "save_paper",
    "save_papers_bulk",
    "upload_file",
    "get_user_preferences",
    "save_user_preferences",
    "save_source_preferences",
    "mock_save_paper",
    "mock_get_citation",
    # API views
    "api_key_management",
    "test_api_key",
    "api_usage_stats",
    # Library views
    "personal_library",
    "api_library_papers",
    "api_library_collections",
    "api_create_collection",
    "api_update_library_paper",
    "api_remove_library_paper",
    # Export views
    "export_bibtex",
    "export_ris",
    "export_endnote",
    "export_csv",
    "export_bulk_citations",
    "export_collection",
    # Annotation views
    "paper_annotations",
    "api_paper_annotations",
    "api_create_annotation",
    "api_update_annotation",
    "api_delete_annotation",
    "api_vote_annotation",
    "api_collaboration_groups",
    "paper_recommendations",
    "user_recommendations",
    # Trending views
    "research_trends",
    "api_trending_papers",
    "api_trending_topics",
    "api_trending_authors",
    "api_research_analytics",
    # BibTeX views
    "bibtex_enrichment",
    "bibtex_upload",
    "bibtex_job_detail",
    "bibtex_job_status",
    "bibtex_download_enriched",
    "bibtex_get_urls",
    "bibtex_job_diff",
    "bibtex_cancel_job",
    "bibtex_resource_status",
    # Repository views
    "list_repositories",
    "create_repository_connection",
    "sync_status",
    "user_repository_stats",
    "RepositoryViewSet",
    "RepositoryConnectionViewSet",
    "DatasetViewSet",
    # Workspace views
    "user_default_workspace",
    # Search API endpoints
    "save_search",
    "get_saved_searches",
    "delete_saved_search",
    "run_saved_search",
    "api_search_arxiv",
    "api_search_pubmed",
    "api_search_semantic",
    "api_search_pmc",
    "api_search_doaj",
    "api_search_biorxiv",
    "api_search_plos",
]


def build_scholar_context(request, current_project=None):
    """Context builder for workspace content endpoint (partial rendering)."""
    library_count = 0
    if request.user.is_authenticated:
        try:
            from apps.workspace.scholar_app.models import UserLibrary

            library_count = UserLibrary.objects.filter(user=request.user).count()
        except Exception:
            pass

    return {
        "current_project": current_project,
        "library_count": library_count,
        "query": "",
        "results": [],
        "has_results": False,
        "user_projects": [],
        "recent_jobs": [],
        "filter_ranges": {
            "year_min": 1900,
            "year_max": 2025,
            "citations_min": 0,
            "citations_max": 128,
            "impact_factor_min": 0,
            "impact_factor_max": 50.0,
        },
    }


# EOF
