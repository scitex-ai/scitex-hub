#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 (auto-generated)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/repository/api/__init__.py
# ----------------------------------------
"""
Repository API Module

Re-exports all repository API endpoints from modular structure.
"""

# File tree navigation
from .file_tree import api_file_tree

# Symlink operations
from .symlink import api_create_symlink

# Bundle extraction
from .extract_bundle import api_extract_bundle

# Directory operations
from .directory import api_concatenate_directory

# Git status operations
from .git_status import api_git_status

# Git operations (stage, unstage, discard, commit, history, diff)
from .git_operations import (
    api_git_stage,
    api_git_unstage,
    api_git_discard,
    api_git_commit,
    api_git_history,
    api_git_diff,
    api_git_stage_all,
    api_git_unstage_all,
)

# SciTeX initialization
from .scitex import api_initialize_scitex_structure

# File CRUD operations
from .file_operations import (
    api_file_create,
    api_file_delete,
    api_file_rename,
    api_file_copy,
    api_file_move,
    api_file_upload,
    api_file_upload_url,
)

# Repository health management
from .repository_health import (
    api_repository_health,
    api_repository_cleanup,
    api_repository_sync,
    api_repository_restore,
)

# Permission utilities (internal use)
from .permissions import (
    check_project_read_access,
    check_project_write_access,
    check_user_repository_access,
)

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
    # Repository health
    "api_repository_health",
    "api_repository_cleanup",
    "api_repository_sync",
    "api_repository_restore",
    # Permissions (internal)
    "check_project_read_access",
    "check_project_write_access",
    "check_user_repository_access",
]

# EOF
