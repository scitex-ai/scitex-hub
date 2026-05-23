#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 (auto-generated)"
# File: /home/ywatanabe/proj/scitex-hub/apps/project_app/views/repository/api/__init__.py
# ----------------------------------------
"""
Repository API Module

Re-exports all repository API endpoints from modular structure.
"""

# File tree navigation
# App submission API
from .app_submission import (
    api_app_scaffold,
    api_app_status,
    api_app_submit,
    api_app_validate,
)

# Directory operations
from .directory import api_concatenate_directory

# Bundle extraction
from .extract_bundle import api_extract_bundle

# File CRUD operations
from .file_operations import (
    api_file_copy,
    api_file_create,
    api_file_delete,
    api_file_move,
    api_file_rename,
    api_file_upload,
    api_file_upload_url,
)
from .file_tree import api_file_tree

# Git operations (stage, unstage, discard, commit, history, diff, push, pull)
from .git_operations import (
    api_git_commit,
    api_git_diff,
    api_git_discard,
    api_git_history,
    api_git_pull,
    api_git_push,
    api_git_stage,
    api_git_stage_all,
    api_git_unstage,
    api_git_unstage_all,
)

# Git status operations
from .git_status import api_git_status

# Permission utilities (internal use)
from .permissions import (
    check_project_read_access,
    check_project_write_access,
    check_user_repository_access,
)

# Repository health management
from .repository_health import (
    api_repository_cleanup,
    api_repository_health,
    api_repository_restore,
    api_repository_sync,
)

# SciTeX initialization
from .scitex import api_initialize_scitex_structure

# Symlink operations
from .symlink import api_create_symlink

__all__ = [
    # File operations
    "api_file_tree",
    "api_create_symlink",
    "api_extract_bundle",
    "api_concatenate_directory",
    "api_git_status",
    "api_initialize_scitex_structure",
    # File CRUD
    "api_file_create",
    "api_file_delete",
    "api_file_rename",
    "api_file_copy",
    "api_file_move",
    "api_file_upload",
    "api_file_upload_url",
    # Git operations
    "api_git_stage",
    "api_git_unstage",
    "api_git_discard",
    "api_git_commit",
    "api_git_history",
    "api_git_diff",
    "api_git_stage_all",
    "api_git_unstage_all",
    "api_git_push",
    "api_git_pull",
    # Repository health
    "api_repository_health",
    "api_repository_cleanup",
    "api_repository_sync",
    "api_repository_restore",
    # App submission
    "api_app_validate",
    "api_app_submit",
    "api_app_status",
    "api_app_scaffold",
    # Permissions (internal)
    "check_project_read_access",
    "check_project_write_access",
    "check_user_repository_access",
]

# EOF
