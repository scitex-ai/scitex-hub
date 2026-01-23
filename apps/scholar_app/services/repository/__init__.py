"""
Repository services - Dataset and DOI management
"""

from .services import *
from .doi_exceptions import (
    DOIServiceError,
    DOIMetadataError,
    DOIAssignmentError,
)
from .doi_metadata_builder import DatasetMetadataBuilder
from .paper_metadata_builder import PaperMetadataBuilder
from .doi_manager import DOIManager
from .citation_formatter import CitationFormatter
from .doi_utils import (
    auto_assign_doi_on_publish,
    validate_and_format_doi,
    get_doi_metadata,
)

__all__ = [
    "RepositoryServiceError",
    "AuthenticationError",
    "APIError",
    "ValidationError",
    "BaseRepositoryService",
    "RepositoryServiceFactory",
    "DOIServiceError",
    "DOIMetadataError",
    "DOIAssignmentError",
    "DatasetMetadataBuilder",
    "PaperMetadataBuilder",
    "DOIManager",
    "CitationFormatter",
    "auto_assign_doi_on_publish",
    "validate_and_format_doi",
    "get_doi_metadata",
]
