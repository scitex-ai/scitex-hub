#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar app URLs - BibTeX endpoints."""

from __future__ import annotations

from django.urls import path

from ..views import bibtex as bibtex_views

# BibTeX Enrichment pages
page_patterns = [
    path(
        "bibtex/enrichment/", bibtex_views.bibtex_enrichment, name="bibtex_enrichment"
    ),
    path("bibtex/preview/", bibtex_views.bibtex_preview, name="bibtex_preview"),
    path("bibtex/upload/", bibtex_views.bibtex_upload, name="bibtex_upload"),
    path(
        "bibtex/job/<uuid:job_id>/",
        bibtex_views.bibtex_job_detail,
        name="bibtex_job_detail",
    ),
]

# BibTeX API endpoints
api_patterns = [
    path(
        "api/bibtex/enrich/", bibtex_views.bibtex_enrich_sync, name="bibtex_enrich_sync"
    ),
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
]

urlpatterns = page_patterns + api_patterns


# EOF
