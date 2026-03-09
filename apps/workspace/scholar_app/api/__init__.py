#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scholar App API Layer

This package contains REST API components for the Scholar application.
"""

from . import public_search
from .permissions import (
    CanAccessAnnotation,
    CanAccessCollection,
    CanAccessPaper,
    IsOwner,
    IsOwnerOrReadOnly,
)
from .serializers import (
    AnnotationSerializer,
    CollectionSerializer,
    DatasetMetadataSerializer,
    PaperSerializer,
    RepositoryConnectionSerializer,
    SavedSearchSerializer,
)
from .viewsets import (
    AnnotationViewSet,
    CollectionViewSet,
    PaperViewSet,
    SavedSearchViewSet,
)

__all__ = [
    # Serializers
    "PaperSerializer",
    "CollectionSerializer",
    "SavedSearchSerializer",
    "AnnotationSerializer",
    "RepositoryConnectionSerializer",
    "DatasetMetadataSerializer",
    # ViewSets
    "PaperViewSet",
    "CollectionViewSet",
    "SavedSearchViewSet",
    "AnnotationViewSet",
    # Permissions
    "IsOwner",
    "IsOwnerOrReadOnly",
    "CanAccessPaper",
    "CanAccessCollection",
    "CanAccessAnnotation",
    # Public API
    "public_search",
]

# EOF
