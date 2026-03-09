#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repository services for research data repositories - modular structure."""

from .exceptions import (
    RepositoryServiceError,
    AuthenticationError,
    APIError,
    ValidationError,
)
from .base_service import BaseRepositoryService
from .zenodo_service import ZenodoService
from .zenodo_utils import format_zenodo_metadata
from .factory import RepositoryServiceFactory
from .sync_utils import sync_dataset_with_repository, upload_dataset_to_repository

__all__ = [
    # Exceptions
    "RepositoryServiceError",
    "AuthenticationError",
    "APIError",
    "ValidationError",
    # Base
    "BaseRepositoryService",
    # Zenodo
    "ZenodoService",
    "format_zenodo_metadata",
    # Factory
    "RepositoryServiceFactory",
    # Sync utils
    "sync_dataset_with_repository",
    "upload_dataset_to_repository",
]

# EOF
