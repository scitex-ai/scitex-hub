#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Operations API

CRUD operations for files and directories within a project.
Endpoints: create, delete, rename, copy, move, upload, upload_url

Re-exports from specialized submodules:
- file_ops_utils: Utility functions
- file_ops_crud: Basic CRUD (create, delete, rename, copy)
- file_ops_transfer: Transfer operations (move, upload, upload_url)
"""

from __future__ import annotations

# Re-export CRUD operations
from .file_ops_crud import (
    api_file_copy,
    api_file_create,
    api_file_delete,
    api_file_rename,
)

# Re-export transfer operations
from .file_ops_transfer import api_file_move, api_file_upload, api_file_upload_url

# Re-export utilities (for backward compatibility with internal imports)
from .file_ops_utils import get_project_path as _get_project_path
from .file_ops_utils import git_auto_commit as _git_auto_commit
from .file_ops_utils import validate_path as _validate_path

__all__ = [
    # API endpoints
    "api_file_create",
    "api_file_delete",
    "api_file_rename",
    "api_file_copy",
    "api_file_move",
    "api_file_upload",
    "api_file_upload_url",
    # Utilities (internal, prefixed with _)
    "_get_project_path",
    "_validate_path",
    "_git_auto_commit",
]


# EOF
