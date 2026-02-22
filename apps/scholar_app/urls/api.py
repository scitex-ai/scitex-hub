#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar app URLs - External API endpoints (CrossRef, Citation Graph, PDF, Keys)."""

from __future__ import annotations

from django.urls import path

from ..api import api_keys, citation_graph, crossref_proxy, public_search
from ..views.search import pdf_download as pdf_views

# Public Scholar API (v1) - Rate Limited
public_api_patterns = [
    path(
        "api/v1/scholar/search/",
        public_search.search,
        name="public_api_search",
    ),
    path(
        "api/v1/scholar/info/",
        public_search.info,
        name="public_api_info",
    ),
]

# CrossRef Local API (Public Access)
crossref_patterns = [
    path("api/crossref/search/", crossref_proxy.search, name="crossref_api_search"),
    path(
        "api/crossref/citations/",
        crossref_proxy.citations,
        name="crossref_api_citations",
    ),
    path("api/crossref/health/", crossref_proxy.health, name="crossref_api_health"),
    path("api/crossref/stats/", crossref_proxy.stats, name="crossref_api_stats"),
]

# Citation Graph API (Network Analysis) - under scholar_app namespace
citation_graph_patterns = [
    path(
        "citation-graph/network/",
        citation_graph.build_network,
        name="citation_graph_network",
    ),
    path(
        "citation-graph/network/multi/",
        citation_graph.build_network_multi,
        name="citation_graph_network_multi",
    ),
    path(
        "citation-graph/network/query/",
        citation_graph.build_network_query,
        name="citation_graph_network_query",
    ),
    path(
        "citation-graph/related/",
        citation_graph.get_related_papers,
        name="citation_graph_related",
    ),
    path(
        "citation-graph/paper/",
        citation_graph.paper_summary,
        name="citation_graph_paper",
    ),
    path(
        "citation-graph/health/",
        citation_graph.health,
        name="citation_graph_health",
    ),
]

# PDF Download API endpoints
pdf_patterns = [
    path("api/pdf/download/", pdf_views.api_download_pdf, name="api_download_pdf"),
    path(
        "api/pdf/status/", pdf_views.api_check_pdf_status, name="api_check_pdf_status"
    ),
    path(
        "api/pdf/download-bulk/",
        pdf_views.api_download_pdf_bulk,
        name="api_download_pdf_bulk",
    ),
    path("api/pdf/serve/", pdf_views.api_serve_pdf, name="api_serve_pdf"),
]

# API Key Management (RESTful)
api_key_patterns = [
    path("api/keys/", api_keys.list_api_keys, name="api_keys_list"),
    path("api/keys/create/", api_keys.create_api_key, name="api_keys_create"),
    path("api/keys/<uuid:key_id>/", api_keys.update_api_key, name="api_keys_update"),
    path(
        "api/keys/<uuid:key_id>/delete/",
        api_keys.delete_api_key,
        name="api_keys_delete",
    ),
    path("api/keys/info/", api_keys.api_key_info, name="api_keys_info"),
]

# Combine all patterns
urlpatterns = (
    public_api_patterns
    + crossref_patterns
    + citation_graph_patterns
    + pdf_patterns
    + api_key_patterns
)


# EOF
