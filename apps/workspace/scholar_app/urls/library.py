#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar app URLs - Library, Export, and Annotation endpoints."""

from __future__ import annotations

from django.urls import path

from ..views.annotation import views as annotation_views
from ..views.export import views as export_views
from ..views.library import views as library_views
from ..views.trending import views as trending_views

# Citation Export APIs
export_patterns = [
    path("api/export/bibtex/", export_views.export_bibtex, name="export_bibtex"),
    path("api/export/ris/", export_views.export_ris, name="export_ris"),
    path("api/export/endnote/", export_views.export_endnote, name="export_endnote"),
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
]

# Personal Library APIs
library_patterns = [
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
    # Integration status stubs (return available=false until implemented)
    # NOTE: Zotero status is served by the real (login-gated) view in
    # zotero_patterns below, not the stub here.
    path(
        "api/library/connected-papers/status/",
        library_views.api_connected_papers_status,
        name="api_connected_papers_status",
    ),
]

# Project linking endpoints (separate module)
from ..views.library.project_linking import (
    api_link_paper_to_project,
    api_project_papers,
    api_setup_project_workspace,
    api_unlink_paper_from_project,
)

project_linking_patterns = [
    path(
        "api/library/papers/<uuid:paper_id>/link/",
        api_link_paper_to_project,
        name="api_link_paper_to_project",
    ),
    path(
        "api/library/papers/<uuid:paper_id>/unlink/",
        api_unlink_paper_from_project,
        name="api_unlink_paper_from_project",
    ),
    path(
        "api/library/projects/<uuid:project_id>/papers/",
        api_project_papers,
        name="api_project_papers",
    ),
    path(
        "api/library/projects/<uuid:project_id>/setup-workspace/",
        api_setup_project_workspace,
        name="api_setup_project_workspace",
    ),
]

# Zotero integration endpoints (import/collections/tags; status lives in
# library_patterns above as api_zotero_status)
from ..views.library.zotero_import import (
    zotero_collections,
    zotero_import,
    zotero_status,
    zotero_tags,
)

zotero_patterns = [
    path(
        "api/library/zotero/status/",
        zotero_status,
        name="api_zotero_status",
    ),
    path(
        "api/library/zotero/import/",
        zotero_import,
        name="zotero_import",
    ),
    path(
        "api/library/zotero/collections/",
        zotero_collections,
        name="zotero_collections",
    ),
    path(
        "api/library/zotero/tags/",
        zotero_tags,
        name="zotero_tags",
    ),
]

# Research Trend Analysis
trend_patterns = [
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
]

# Collaborative Annotation System
annotation_patterns = [
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
]

# Paper recommendations
recommendation_patterns = [
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
]

# Combine all patterns
urlpatterns = (
    export_patterns
    + library_patterns
    + project_linking_patterns
    + zotero_patterns
    + trend_patterns
    + annotation_patterns
    + recommendation_patterns
)


# EOF
