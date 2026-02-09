#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scholar App Services Layer

This package contains business logic and domain services for the Scholar application.

Services are organized by domain/feature:
    - repository: Data repository integration and DOI management
    - search: Paper search and discovery services
    - bibtex: BibTeX enrichment and processing services
    - library_cache: User library caching and project sharing
    - export_packer: Export packaging and symlink resolution
    - utils: Common utilities for citation formatting and parsing
"""

# Import repository services (DOI & dataset management)
# Import export services
from .export_packer import ExportPackerService

# Import library services
from .library_cache import (
    LibraryCacheService,
    cache_results_for_user,
    get_paper_from_cache,
)
from .repository import (
    auto_assign_doi_on_publish,
    get_doi_metadata,
    sync_dataset_with_repository,
    upload_dataset_to_repository,
    validate_and_format_doi,
)
from .user_library_service import UserLibraryService

__all__ = [
    # DOI Services
    "auto_assign_doi_on_publish",
    "validate_and_format_doi",
    "get_doi_metadata",
    # Repository Services
    "sync_dataset_with_repository",
    "upload_dataset_to_repository",
    # Library Services
    "LibraryCacheService",
    "cache_results_for_user",
    "get_paper_from_cache",
    "UserLibraryService",
    # Export Services
    "ExportPackerService",
]

# EOF
