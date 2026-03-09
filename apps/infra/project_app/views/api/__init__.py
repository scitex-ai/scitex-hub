#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 (auto-generated)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/api/__init__.py
# ----------------------------------------
"""
Project App API Views - Modular Structure

This module provides backward compatibility by re-exporting all API views
from their respective modules.

Split from monolithic api_views.py (583 lines) into:
- file_tree.py: File tree API (115 lines)
- name_availability.py: Name availability checking (106 lines)
- project_crud.py: Project CRUD operations (93 lines)
- directory_concatenation.py: Directory concatenation (159 lines)
- repository_health.py: Repository health management (228 lines)
"""

from __future__ import annotations

# File Tree API
from .file_tree import (
    api_file_tree,
)

# Name Availability API
from .name_availability import (
    api_check_name_availability,
)

# Project CRUD APIs
from .project_crud import (
    api_project_list,
    api_project_create,
    api_project_detail,
)

# Directory Concatenation API
from .directory_concatenation import (
    api_concatenate_directory,
)

# Repository Health Management APIs
from .repository_health import (
    api_repository_health,
    api_repository_cleanup,
    api_repository_sync,
    api_repository_restore,
)

__all__ = [
    # File Tree
    "api_file_tree",
    # Name Availability
    "api_check_name_availability",
    # Project CRUD
    "api_project_list",
    "api_project_create",
    "api_project_detail",
    # Directory Concatenation
    "api_concatenate_directory",
    # Repository Health
    "api_repository_health",
    "api_repository_cleanup",
    "api_repository_sync",
    "api_repository_restore",
]

# EOF
