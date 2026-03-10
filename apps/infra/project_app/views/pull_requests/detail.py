#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pull Request Detail Views

Handles PR detail viewing, reviews, comments, and actions.

Re-exports from specialized submodules:
- detail_views: Main PR detail view
- detail_actions: PR actions (merge, close, reopen)
- detail_comments: Comments and reviews
- detail_utils: Helper functions
"""

from __future__ import annotations

from .detail_actions import pr_close, pr_merge, pr_reopen
from .detail_comments import pr_comment_create, pr_review_submit
from .detail_utils import get_pr_checks, get_pr_diff, get_pr_timeline
from .detail_views import pr_detail

__all__ = [
    # Views
    "pr_detail",
    # Actions
    "pr_merge",
    "pr_close",
    "pr_reopen",
    # Comments/Reviews
    "pr_review_submit",
    "pr_comment_create",
    # Utilities
    "get_pr_diff",
    "get_pr_checks",
    "get_pr_timeline",
]


# EOF
