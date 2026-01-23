#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/bibtex/__init__.py

"""
BibTeX Views Module

Export all BibTeX enrichment views.
"""

from .index import bibtex_enrichment
from .preview import bibtex_preview
from .upload import bibtex_upload
from .job import (
    bibtex_job_detail,
    bibtex_job_status,
    bibtex_job_papers,
    bibtex_recent_jobs,
)
from .download import bibtex_download_enriched, bibtex_download_original
from .enrichment import bibtex_enrich_sync
from .export import bibtex_get_urls, bibtex_save_to_project
from .diff import bibtex_job_diff
from .resource import bibtex_resource_status
from .cancel import bibtex_cancel_job
from .delete import bibtex_delete_job
from .utils import process_bibtex_job

__all__ = [
    # Index
    "bibtex_enrichment",
    # Preview
    "bibtex_preview",
    # Upload
    "bibtex_upload",
    # Job management
    "bibtex_job_detail",
    "bibtex_job_status",
    "bibtex_job_papers",
    "bibtex_recent_jobs",
    # Download
    "bibtex_download_enriched",
    "bibtex_download_original",
    # Enrichment
    "bibtex_enrich_sync",
    # Export
    "bibtex_get_urls",
    "bibtex_save_to_project",
    # Diff
    "bibtex_job_diff",
    # Resource
    "bibtex_resource_status",
    # Cancel
    "bibtex_cancel_job",
    # Delete
    "bibtex_delete_job",
    # Utils
    "process_bibtex_job",
]

# EOF
