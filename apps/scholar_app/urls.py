#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-16 18:41:37 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/urls.py


from django.urls import path
from django.urls import include
from rest_framework.routers import DefaultRouter
from .views.search import views as search_views
from .views import bibtex as bibtex_views
from .views.workspace import api_key_views
from .views.workspace import views as workspace_views
from .views.library import views as library_views
from .views.export import views as export_views
from .views.annotation import views as annotation_views
from .views.trending import views as trending_views
from .views import repository as repository_views
from .integrations import scitex as scitex_search
from .api import crossref_proxy

app_name = "scholar_app"

# Repository API Router
router = DefaultRouter()
router.register(
    r"repositories",
    repository_views.RepositoryViewSet,
    basename="repositories",
)
router.register(
    r"connections",
    repository_views.RepositoryConnectionViewSet,
    basename="connections",
)
router.register(
    r"datasets", repository_views.DatasetViewSet, basename="datasets"
)

urlpatterns = [
    # Default workspace for logged-in users without project
    path(
        "workspace/",
        workspace_views.user_default_workspace,
        name="user_default_workspace",
    ),
    # MVP Simple Interface - Separate pages instead of tabs
    path("", search_views.scholar_bibtex, name="index"),
    path("bibtex/", search_views.scholar_bibtex, name="scholar_bibtex"),  # Keep for backwards compatibility
    path("search/", search_views.scholar_search, name="scholar_search"),
    # path('search/', search_views.simple_search, name='simple_search'),
    # path('project/<int:project_id>/search/', search_views.project_search, name='project_search'),
    # path('project/<int:project_id>/library/', search_views.project_library, name='project_library'),
    # path('library/', search_views.personal_library, name='personal_library'),
    # path('features/', search_views.features, name='features'),
    # path('pricing/', search_views.pricing, name='pricing'),
    # MVP API endpoints
    path("api/save-paper/", search_views.save_paper, name="save_paper"),
    path(
        "api/papers/save/", search_views.save_paper, name="papers_save"
    ),  # RESTful endpoint
    path(
        "api/papers/save-bulk/",
        search_views.save_papers_bulk,
        name="papers_save_bulk",
    ),  # Bulk save endpoint
    path("api/upload-file/", search_views.upload_file, name="upload_file"),
    path("api/get-citation/", search_views.get_citation, name="get_citation"),
    # User Preferences API endpoints
    path(
        "api/preferences/",
        search_views.get_user_preferences,
        name="get_user_preferences",
    ),
    path(
        "api/preferences/save/",
        search_views.save_user_preferences,
        name="save_user_preferences",
    ),
    path(
        "api/preferences/sources/",
        search_views.save_source_preferences,
        name="save_source_preferences",
    ),
    # API Key Management endpoints
    path("api-keys/", api_key_views.api_key_management, name="api_keys"),
    path("api/test-api-key/", api_key_views.test_api_key, name="test_api_key"),
    path(
        "api/usage-stats/",
        api_key_views.api_usage_stats,
        name="api_usage_stats",
    ),
    # Saved Search API endpoints
    path("api/save-search/", search_views.save_search, name="save_search"),
    path(
        "api/saved-searches/",
        search_views.get_saved_searches,
        name="get_saved_searches",
    ),
    path(
        "api/saved-searches/<uuid:search_id>/delete/",
        search_views.delete_saved_search,
        name="delete_saved_search",
    ),
    path(
        "api/saved-searches/<uuid:search_id>/run/",
        search_views.run_saved_search,
        name="run_saved_search",
    ),
    # Progressive search API endpoints
    path(
        "api/search/arxiv/",
        search_views.api_search_arxiv,
        name="api_search_arxiv",
    ),
    path(
        "api/search/pubmed/",
        search_views.api_search_pubmed,
        name="api_search_pubmed",
    ),
    path(
        "api/search/semantic/",
        search_views.api_search_semantic,
        name="api_search_semantic",
    ),
    path(
        "api/search/pmc/", search_views.api_search_pmc, name="api_search_pmc"
    ),
    path(
        "api/search/doaj/",
        search_views.api_search_doaj,
        name="api_search_doaj",
    ),
    path(
        "api/search/biorxiv/",
        search_views.api_search_biorxiv,
        name="api_search_biorxiv",
    ),
    path(
        "api/search/plos/",
        search_views.api_search_plos,
        name="api_search_plos",
    ),
    # SciTeX integrated search endpoints
    path(
        "api/search/scitex/",
        scitex_search.api_scitex_search,
        name="api_scitex_search",
    ),
    path(
        "api/search/scitex/single/",
        scitex_search.api_scitex_search_single,
        name="api_scitex_search_single",
    ),
    path(
        "api/search/scitex/capabilities/",
        scitex_search.api_scitex_capabilities,
        name="api_scitex_capabilities",
    ),
    # Citation Export endpoints
    path(
        "api/export/bibtex/", export_views.export_bibtex, name="export_bibtex"
    ),
    path("api/export/ris/", export_views.export_ris, name="export_ris"),
    path(
        "api/export/endnote/",
        export_views.export_endnote,
        name="export_endnote",
    ),
    path("api/export/csv/", export_views.export_csv, name="export_csv"),
    path(
        "api/export/bulk/",
        export_views.export_bulk_citations,
        name="export_bulk_citations",
    ),
    path(
        "api/export/collection/<uuid:collection_id>/",
        export_views.export_collection,
        name="export_collection",
    ),
    # Personal Library API endpoints
    path(
        "api/library/papers/",
        library_views.api_library_papers,
        name="api_library_papers",
    ),
    path(
        "api/library/collections/",
        library_views.api_library_collections,
        name="api_library_collections",
    ),
    path(
        "api/library/collections/create/",
        library_views.api_create_collection,
        name="api_create_collection",
    ),
    path(
        "api/library/papers/<uuid:paper_id>/update/",
        library_views.api_update_library_paper,
        name="api_update_library_paper",
    ),
    path(
        "api/library/papers/<uuid:paper_id>/remove/",
        library_views.api_remove_library_paper,
        name="api_remove_library_paper",
    ),
    # Research Trend Analysis endpoints
    path("trends/", trending_views.research_trends, name="research_trends"),
    path(
        "api/trends/papers/",
        trending_views.api_trending_papers,
        name="api_trending_papers",
    ),
    path(
        "api/trends/topics/",
        trending_views.api_trending_topics,
        name="api_trending_topics",
    ),
    path(
        "api/trends/authors/",
        trending_views.api_trending_authors,
        name="api_trending_authors",
    ),
    path(
        "api/trends/analytics/",
        trending_views.api_research_analytics,
        name="api_research_analytics",
    ),
    # Collaborative Annotation System endpoints
    path(
        "annotations/<uuid:paper_id>/",
        annotation_views.paper_annotations,
        name="paper_annotations",
    ),
    path(
        "api/annotations/<uuid:paper_id>/",
        annotation_views.api_paper_annotations,
        name="api_paper_annotations",
    ),
    path(
        "api/annotations/create/",
        annotation_views.api_create_annotation,
        name="api_create_annotation",
    ),
    path(
        "api/annotations/<uuid:annotation_id>/update/",
        annotation_views.api_update_annotation,
        name="api_update_annotation",
    ),
    path(
        "api/annotations/<uuid:annotation_id>/delete/",
        annotation_views.api_delete_annotation,
        name="api_delete_annotation",
    ),
    path(
        "api/annotations/<uuid:annotation_id>/vote/",
        annotation_views.api_vote_annotation,
        name="api_vote_annotation",
    ),
    path(
        "api/collaboration/groups/",
        annotation_views.api_collaboration_groups,
        name="api_collaboration_groups",
    ),
    # Paper Similarity Recommendations endpoints
    path(
        "api/recommendations/paper/<uuid:paper_id>/",
        annotation_views.paper_recommendations,
        name="paper_recommendations",
    ),
    path(
        "api/recommendations/user/",
        annotation_views.user_recommendations,
        name="user_recommendations",
    ),
    # BibTeX Enrichment
    path(
        "bibtex/enrichment/",
        bibtex_views.bibtex_enrichment,
        name="bibtex_enrichment",
    ),
    path(
        "bibtex/preview/", bibtex_views.bibtex_preview, name="bibtex_preview"
    ),
    path("bibtex/upload/", bibtex_views.bibtex_upload, name="bibtex_upload"),
    # Simple synchronous API endpoint
    path(
        "api/bibtex/enrich/",
        bibtex_views.bibtex_enrich_sync,
        name="bibtex_enrich_sync",
    ),
    path(
        "bibtex/job/<uuid:job_id>/",
        bibtex_views.bibtex_job_detail,
        name="bibtex_job_detail",
    ),
    # API endpoints
    path(
        "api/bibtex/job/<uuid:job_id>/status/",
        bibtex_views.bibtex_job_status,
        name="bibtex_job_status",
    ),
    path(
        "api/bibtex/job/<uuid:job_id>/papers/",
        bibtex_views.bibtex_job_papers,
        name="bibtex_job_papers",
    ),
    path(
        "api/bibtex/job/<uuid:job_id>/download/",
        bibtex_views.bibtex_download_enriched,
        name="bibtex_download_enriched",
    ),
    path(
        "api/bibtex/job/<uuid:job_id>/download/original/",
        bibtex_views.bibtex_download_original,
        name="bibtex_download_original",
    ),
    path(
        "api/bibtex/job/<uuid:job_id>/urls/",
        bibtex_views.bibtex_get_urls,
        name="bibtex_get_urls",
    ),
    path(
        "api/bibtex/job/<uuid:job_id>/diff/",
        bibtex_views.bibtex_job_diff,
        name="bibtex_job_diff",
    ),
    path(
        "api/bibtex/job/<uuid:job_id>/cancel/",
        bibtex_views.bibtex_cancel_job,
        name="bibtex_cancel_job",
    ),
    path(
        "api/bibtex/job/<uuid:job_id>/delete/",
        bibtex_views.bibtex_delete_job,
        name="bibtex_delete_job",
    ),
    path(
        "api/bibtex/job/<uuid:job_id>/save-to-project/",
        bibtex_views.bibtex_save_to_project,
        name="bibtex_save_to_project",
    ),
    path(
        "api/bibtex/recent-jobs/",
        bibtex_views.bibtex_recent_jobs,
        name="bibtex_recent_jobs",
    ),
    path(
        "api/bibtex/resource-status/",
        bibtex_views.bibtex_resource_status,
        name="bibtex_resource_status",
    ),
    # Legacy mock endpoints
    path(
        "api/mock/save-paper/",
        search_views.mock_save_paper,
        name="mock_save_paper",
    ),
    path(
        "api/mock/get-citation/",
        search_views.mock_get_citation,
        name="mock_get_citation",
    ),
    # Repository Management API
    path("api/repository/", include(router.urls)),
    path(
        "api/repository/sync/<uuid:sync_id>/status/",
        repository_views.sync_status,
        name="sync_status",
    ),
    path(
        "api/repository/stats/",
        repository_views.user_repository_stats,
        name="user_repository_stats",
    ),
    # Legacy repository endpoints
    path(
        "api/repositories/",
        repository_views.list_repositories,
        name="list_repositories",
    ),
    path(
        "api/repository-connections/create/",
        repository_views.create_repository_connection,
        name="create_repository_connection",
    ),
    # CrossRef Local API (Public Access)
    path(
        "api/crossref/search/",
        crossref_proxy.search,
        name="crossref_api_search",
    ),
    path(
        "api/crossref/citations/",
        crossref_proxy.citations,
        name="crossref_api_citations",
    ),
    path(
        "api/crossref/health/",
        crossref_proxy.health,
        name="crossref_api_health",
    ),
    path(
        "api/crossref/stats/",
        crossref_proxy.stats,
        name="crossref_api_stats",
    ),
    # Advanced features (for future implementation)
    # path('advanced/dashboard/', views.search_dashboard, name='search_dashboard'),
    # path('advanced/search/', views.advanced_search, name='advanced_search'),
    # path('advanced/paper/<uuid:paper_id>/', views.paper_detail, name='paper_detail'),
    # path('advanced/author/<uuid:author_id>/', views.author_profile, name='author_profile'),
    # path('advanced/saved/', views.saved_searches, name='saved_searches'),
    # path('advanced/trending/', views.trending_papers, name='trending_papers'),
]

# EOF
