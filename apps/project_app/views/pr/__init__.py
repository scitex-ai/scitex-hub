"""
Pull Request Views Module

Re-exports all PR-related views for backward compatibility.
"""

# List views
from .list_views import pr_list, pr_compare

# Detail views
from .detail_views import pr_detail, pr_create

# Action views
from .actions import pr_merge, pr_close, pr_reopen

# Review views
from .review import pr_review_submit, pr_comment_create

# Utilities
from .utils import (
    get_project_branches,
    compare_branches,
    get_pr_diff,
    get_pr_checks,
    get_pr_timeline,
    sync_pr_commits,
    check_pr_conflicts,
)

__all__ = [
    # List views
    "pr_list",
    "pr_compare",
    # Detail views
    "pr_detail",
    "pr_create",
    # Actions
    "pr_merge",
    "pr_close",
    "pr_reopen",
    # Review
    "pr_review_submit",
    "pr_comment_create",
    # Utils
    "get_project_branches",
    "compare_branches",
    "get_pr_diff",
    "get_pr_checks",
    "get_pr_timeline",
    "sync_pr_commits",
    "check_pr_conflicts",
]
