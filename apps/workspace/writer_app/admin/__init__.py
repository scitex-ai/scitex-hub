from django.contrib import admin
from .editor import ManuscriptAdmin
from .compilation import CompilationJobAdmin, AIAssistanceLogAdmin
from .version_control import ManuscriptVersionAdmin, ManuscriptBranchAdmin
from .arxiv import ArxivSubmissionAdmin, ArxivAccountAdmin
from .collaboration import WriterPresenceAdmin, CollaborativeSessionAdmin
