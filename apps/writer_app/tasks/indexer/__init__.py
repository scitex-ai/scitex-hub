#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Indexer tasks - modular structure.

This __init__.py re-exports all functions to maintain backward compatibility
with existing code that imports from apps.writer_app.tasks.indexer.
"""

from .constants import CELERY_AVAILABLE, shared_task
from .constants import SUPPORTED_FIGURE_EXTENSIONS, SUPPORTED_TABLE_EXTENSIONS
from .indexing import index_project_figures, index_project_tables
from .metadata import (
    compute_file_hash,
    extract_figure_metadata,
    extract_table_metadata,
    detect_source,
    extract_tags,
)
from .references import update_latex_references
from .thumbnails import generate_thumbnail, generate_table_thumbnail

__all__ = [
    # Constants
    "CELERY_AVAILABLE",
    "shared_task",
    "SUPPORTED_FIGURE_EXTENSIONS",
    "SUPPORTED_TABLE_EXTENSIONS",
    # Indexing tasks
    "index_project_figures",
    "index_project_tables",
    # Metadata extraction
    "compute_file_hash",
    "extract_figure_metadata",
    "extract_table_metadata",
    "detect_source",
    "extract_tags",
    # Reference tracking
    "update_latex_references",
    # Thumbnail generation
    "generate_thumbnail",
    "generate_table_thumbnail",
]

# EOF
