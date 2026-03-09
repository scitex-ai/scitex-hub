"""Writer app models - Feature-based organization."""

# Editor models
from .editor.document import Manuscript
from .editor.section import ManuscriptSection
from .editor.references import Citation, Figure, Table

# Compilation models
from .compilation.compilation import CompilationJob, AIAssistanceLog

# Version control models
from .version_control.version import (
    ManuscriptVersion,
    ManuscriptBranch,
    DiffResult,
    MergeRequest,
)

# arXiv integration models
from .arxiv.submission import (
    ArxivAccount,
    ArxivCategory,
    ArxivSubmission,
    ArxivSubmissionHistory,
    ArxivValidationResult,
    ArxivApiResponse,
)

# Collaboration models
from .collaboration.session import WriterPresence, CollaborativeSession

__all__ = [
    # Editor
    "Manuscript",
    "ManuscriptSection",
    "Citation",
    "Figure",
    "Table",
    # Compilation
    "CompilationJob",
    "AIAssistanceLog",
    # Version Control
    "ManuscriptVersion",
    "ManuscriptBranch",
    "DiffResult",
    "MergeRequest",
    # arXiv
    "ArxivAccount",
    "ArxivCategory",
    "ArxivSubmission",
    "ArxivSubmissionHistory",
    "ArxivValidationResult",
    "ArxivApiResponse",
    # Collaboration
    "WriterPresence",
    "CollaborativeSession",
]
