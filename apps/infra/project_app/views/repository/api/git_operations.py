#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git Operations API

Provides endpoints for git operations:
- Stage/unstage files
- Discard changes
- Commit changes
- View history
- View diff

Re-exports from specialized submodules:
- git_utils: Utility functions for git command execution
- git_staging: Stage/unstage operations
- git_commit: Commit and discard operations
- git_history: History and diff operations
"""

# Re-export all views for backward compatibility
from .git_commit import api_git_commit, api_git_discard
from .git_history import api_git_diff, api_git_history

# Remote operations
from .git_remote import api_git_pull, api_git_push
from .git_staging import (
    api_git_stage,
    api_git_stage_all,
    api_git_unstage,
    api_git_unstage_all,
)

# Also export utilities for internal use
from .git_utils import get_project_path, run_git_command

__all__ = [
    # Staging operations
    "api_git_stage",
    "api_git_unstage",
    "api_git_stage_all",
    "api_git_unstage_all",
    # Commit operations
    "api_git_commit",
    "api_git_discard",
    # History operations
    "api_git_history",
    "api_git_diff",
    # Remote operations
    "api_git_push",
    "api_git_pull",
    # Utilities
    "get_project_path",
    "run_git_command",
]


# EOF
