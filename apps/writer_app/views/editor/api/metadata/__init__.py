#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/views/editor/api/metadata/__init__.py
"""Metadata API endpoints - sections config, citations, bibliography, file tree.

This module has been refactored into separate files for better maintainability:
- section_scanner.py: Section scanning logic
- sections.py: Section configuration view
- citations.py: Citations API
- bibliography.py: Bibliography regeneration
- file_tree.py: File tree API for sidebar navigation

Backward compatibility exports are provided below.
"""

from __future__ import annotations

# Import all views for backward compatibility
from .section_scanner import _scan_project_sections
from .sections import sections_config_view
from .citations import citations_api
from .bibliography import regenerate_bibliography_api
from .file_tree import file_tree_view

# Public API
__all__ = [
    # Section views
    "sections_config_view",
    "file_tree_view",
    "_scan_project_sections",
    # Citation views
    "citations_api",
    # Bibliography views
    "regenerate_bibliography_api",
]

# EOF
