#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/pull_requests/__init__.py
# ----------------------------------------
"""
Pull Requests Feature Views

Exports all pull request-related view functions.
"""

from .list import pr_list
from .detail import (
    pr_detail,
    pr_merge,
    pr_review_submit,
    pr_comment_create,
    pr_close,
    pr_reopen,
)
from .form import pr_create, pr_compare

__all__ = [
    # List
    "pr_list",
    # Detail and actions
    "pr_detail",
    "pr_merge",
    "pr_review_submit",
    "pr_comment_create",
    "pr_close",
    "pr_reopen",
    # Form
    "pr_create",
    "pr_compare",
]

# EOF
