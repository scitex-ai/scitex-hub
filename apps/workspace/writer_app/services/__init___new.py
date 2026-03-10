"""
Writer App Services - Feature-based Service Layer

This module provides a clean service layer organized by feature domains:
- editor: Document and manuscript management
- compilation: LaTeX compilation and AI assistance
- version_control: Version control, branching, and merging
- arxiv: arXiv integration and submission
- collaboration: Real-time collaborative editing

All services follow Django best practices and provide transaction management,
proper error handling, and permission checks.

Usage:
    from apps.workspace.writer_app.services import (
        DocumentService,
        CompilerService,
        VersionControlService,
        ArxivService,
        CollaborationService
    )

Legacy Note:
    This replaces the old WriterService-based approach with a more modular
    feature-based architecture. Old services remain in place during migration.
"""

from .editor import DocumentService
from .compilation import CompilerService
from .version_control import VersionControlService
from .collaboration import CollaborationService

# Note: ArxivService intentionally excluded until migration from arxiv/arxiv_service.py
# from .arxiv import ArxivService

__all__ = [
    "DocumentService",
    "CompilerService",
    "VersionControlService",
    "CollaborationService",
    # 'ArxivService',  # To be added after migration
]

# Legacy exports for backward compatibility during migration
# These will be removed once all views are updated

__legacy_exports__ = [
    "WriterService",
]
