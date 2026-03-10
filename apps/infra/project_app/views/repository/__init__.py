#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/repository/__init__.py
# ----------------------------------------
"""
Repository Feature Views

Exports all repository-related view functions.
"""

from .browse import project_directory_dynamic, project_directory
from .file_view import project_file_view
from .file_edit import project_file_edit
from .file_history import file_history_view
from .commit_detail import commit_detail
from .api import (
    api_file_tree,
    api_create_symlink,
    api_concatenate_directory,
    api_git_status,
    api_initialize_scitex_structure,
    api_repository_health,
    api_repository_cleanup,
    api_repository_sync,
    api_repository_restore,
)

__all__ = [
    # Browse
    "project_directory_dynamic",
    "project_directory",
    # File operations
    "project_file_view",
    "project_file_edit",
    # History
    "file_history_view",
    "commit_detail",
    # APIs
    "api_file_tree",
    "api_create_symlink",
    "api_concatenate_directory",
    "api_git_status",
    "api_initialize_scitex_structure",
    "api_repository_health",
    "api_repository_cleanup",
    "api_repository_sync",
    "api_repository_restore",
]

# EOF
