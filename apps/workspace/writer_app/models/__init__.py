"""Writer app models - Feature-based organization."""

# Editor models
# arXiv integration models
from .arxiv.submission import (
    ArxivAccount,
    ArxivApiResponse,
    ArxivCategory,
    ArxivSubmission,
    ArxivSubmissionHistory,
    ArxivValidationResult,
)

# Collaboration models
from .collaboration.comment import Comment
from .collaboration.edit import CollaborativeEdit
from .collaboration.invitation import CollaborationInvitation
from .collaboration.session import CollaborativeSession, WriterPresence

# Compilation models
from .compilation.compilation import AIAssistanceLog, CompilationJob
from .editor.document import Manuscript
from .editor.references import Citation, Figure, Table
from .editor.section import ManuscriptSection

# Version control models
from .version_control.version import (
    DiffResult,
    ManuscriptBranch,
    ManuscriptVersion,
    MergeRequest,
)

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
    "CollaborationInvitation",
    "CollaborativeEdit",
    "Comment",
]
