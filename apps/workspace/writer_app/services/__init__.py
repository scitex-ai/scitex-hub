"""
Writer App Services - Feature-Organized Services

Business logic layer organized by feature domain.
"""

# Core services
from .writer import WriterService

try:
    from .editor import DocumentService
except ImportError:
    DocumentService = None

try:
    from .compilation import CompilerService
except ImportError:
    CompilerService = None

try:
    from .version_control import VersionControlService
except ImportError:
    VersionControlService = None

try:
    from .arxiv import ArxivService
except ImportError:
    ArxivService = None

try:
    from .collaboration import CollaborationService
except ImportError:
    CollaborationService = None

__all__ = [
    "WriterService",
    "DocumentService",
    "CompilerService",
    "VersionControlService",
    "ArxivService",
    "CollaborationService",
]
