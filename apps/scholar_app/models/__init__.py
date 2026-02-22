#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scholar App Models Package

Organized by domain for maintainability:
    - core: Core entities (papers, authors, journals)
    - search: Search and discovery
    - library: User library and collections
    - collaboration: Annotations and groups
    - bibtex: BibTeX enrichment
"""

# Core models
# Annotation models (collaboration feature)
from .annotation import (
    Annotation,
    AnnotationReply,
    AnnotationTag,
    AnnotationVote,
    CollaborationGroup,
    GroupMembership,
)

# BibTeX models
from .bibtex import (
    BibTeXEnrichmentJob,
)
from .core import (
    Author,
    AuthorPaper,
    Citation,
    Journal,
    SearchIndex,
    Topic,
)

# Graph models
from .graph import (
    SavedGraph,
)

# Library models
from .library import (
    Collection,
    LibraryExport,
    RecommendationLog,
    UserLibrary,
    UserPreference,
)

# Repository models
from .repository import (
    Dataset,
    DatasetFile,
    DatasetVersion,
    Repository,
    RepositoryConnection,
    RepositorySync,
)

# Search models
from .search import (
    SavedSearch,
    SearchFilter,
    SearchQuery,
    SearchResult,
)

# Export all models
__all__ = [
    # Core
    "Author",
    "AuthorPaper",
    "Journal",
    "Topic",
    "SearchIndex",
    "Citation",
    # Search
    "SearchQuery",
    "SearchResult",
    "SearchFilter",
    "SavedSearch",
    # Library
    "Collection",
    "UserLibrary",
    "LibraryExport",
    "RecommendationLog",
    "UserPreference",
    # Collaboration
    "Annotation",
    "AnnotationReply",
    "AnnotationVote",
    "AnnotationTag",
    "CollaborationGroup",
    "GroupMembership",
    # Graph
    "SavedGraph",
    # BibTeX
    "BibTeXEnrichmentJob",
    # Repository
    "Repository",
    "RepositoryConnection",
    "Dataset",
    "DatasetFile",
    "DatasetVersion",
    "RepositorySync",
]

# EOF
