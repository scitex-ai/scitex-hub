"""
Issues feature views
GitHub-style issue tracking for SciTeX projects
"""

from .list import issues_list
from .detail import issue_detail
from .form import issue_create, issue_edit, issue_comment_create
from .management import issue_label_manage, issue_milestone_manage
from .api import (
    api_issue_comment,
    api_issue_close,
    api_issue_reopen,
    api_issue_assign,
    api_issue_label,
    api_issue_milestone,
    api_issue_search,
)

__all__ = [
    # List view
    "issues_list",
    # Detail view
    "issue_detail",
    # Form views (create, edit, comment)
    "issue_create",
    "issue_edit",
    "issue_comment_create",
    # Management views (labels, milestones)
    "issue_label_manage",
    "issue_milestone_manage",
    # API views
    "api_issue_comment",
    "api_issue_close",
    "api_issue_reopen",
    "api_issue_assign",
    "api_issue_label",
    "api_issue_milestone",
    "api_issue_search",
]
