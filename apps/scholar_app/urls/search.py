#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar app URLs - Search endpoints."""

from __future__ import annotations

from django.urls import path

from ..integrations import scitex as scitex_search
from ..views.search import views as search_views

# Main search pages
page_patterns = [
    path("", search_views.scholar_unified, name="index"),
    path("bibtex/", search_views.scholar_bibtex, name="scholar_bibtex"),
    path("search/", search_views.scholar_search, name="scholar_search"),
    path("graph/", search_views.scholar_graph, name="scholar_graph"),
]

# Paper save and citation APIs
paper_api_patterns = [
    path("api/save-paper/", search_views.save_paper, name="save_paper"),
    path("api/papers/save/", search_views.save_paper, name="papers_save"),
    path(
        "api/papers/save-bulk/", search_views.save_papers_bulk, name="papers_save_bulk"
    ),
    path("api/upload-file/", search_views.upload_file, name="upload_file"),
    path("api/get-citation/", search_views.get_citation, name="get_citation"),
]

# User preferences APIs
preferences_patterns = [
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
]

# Saved search APIs
saved_search_patterns = [
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
]

# Progressive search source APIs
source_api_patterns = [
    path("api/search/arxiv/", search_views.api_search_arxiv, name="api_search_arxiv"),
    path(
        "api/search/pubmed/", search_views.api_search_pubmed, name="api_search_pubmed"
    ),
    path(
        "api/search/semantic/",
        search_views.api_search_semantic,
        name="api_search_semantic",
    ),
    path("api/search/pmc/", search_views.api_search_pmc, name="api_search_pmc"),
    path("api/search/doaj/", search_views.api_search_doaj, name="api_search_doaj"),
    path(
        "api/search/biorxiv/",
        search_views.api_search_biorxiv,
        name="api_search_biorxiv",
    ),
    path("api/search/plos/", search_views.api_search_plos, name="api_search_plos"),
    path(
        "api/search/crossref/",
        search_views.api_search_crossref,
        name="api_search_crossref",
    ),
    path(
        "api/search/crossref-local/",
        search_views.api_search_crossref_local,
        name="api_search_crossref_local",
    ),
    path(
        "api/search/openalex/",
        search_views.api_search_openalex,
        name="api_search_openalex",
    ),
]

# Unified and SciTeX search APIs
unified_api_patterns = [
    path("api/search/", search_views.api_search_unified, name="api_search_unified"),
    path(
        "api/search/syntax/",
        search_views.api_search_syntax_help,
        name="api_search_syntax_help",
    ),
    path(
        "api/search/scitex/", scitex_search.api_scitex_search, name="api_scitex_search"
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
]

# Mock endpoints (legacy)
mock_patterns = [
    path("api/mock/save-paper/", search_views.mock_save_paper, name="mock_save_paper"),
    path(
        "api/mock/get-citation/",
        search_views.mock_get_citation,
        name="mock_get_citation",
    ),
]

# Combine all patterns
urlpatterns = (
    page_patterns
    + paper_api_patterns
    + preferences_patterns
    + saved_search_patterns
    + source_api_patterns
    + unified_api_patterns
    + mock_patterns
)


# EOF
