#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/directory_views/__init__.py
# ----------------------------------------
"""
Directory Views Package

This package contains modular views for directory browsing and file history.
"""

from .browse import project_directory_dynamic, project_directory
from .history import file_history_view, commit_detail
from .file_view import project_file_view

__all__ = [
    "project_directory_dynamic",
    "project_directory",
    "file_history_view",
    "commit_detail",
    "project_file_view",
]

# EOF
