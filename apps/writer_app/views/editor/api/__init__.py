#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/views/editor/api/__init__.py
"""
API endpoints for editor operations.

This module exports all API views for backward compatibility.
The monolithic api.py file has been split into focused modules:

- content.py: Section CRUD operations (read, write, save)
- compilation.py: Compilation endpoints (preview, full, status)
- metadata.py: Sections config, citations, bibliography
- files.py: PDF serving, thumbnails
- media.py: Figures and tables management
- section_management.py: Section create/delete/toggle/move
"""

from __future__ import annotations

# Content operations
from .content import (
    section_view,
    save_sections_view,
    # Temporary stubs
    section_history_view,
    section_diff_view,
    section_checkout_view,
    section_commit_view,
    read_tex_file_view,
    available_sections_view,
    presence_update_view,
)

# Compilation operations
from .compilation import (
    compile_api,
    compilation_status_api,
    compile_full_view,
    compilation_job_status,
    # Aliases
    compile_preview_view,
    compile_view,
    preview_pdf_view,
)

# Metadata operations
from .metadata import (
    sections_config_view,
    citations_api,
    regenerate_bibliography_api,
    # Alias
    file_tree_view,
)

# File operations
from .files import (
    pdf_view,
    presence_list_view,
    thumbnail_view,
)

# Media operations
from .media import (
    figures_api,
    tables_api,
    refresh_figures_index,
    refresh_tables_index,
    upload_figures,
    upload_tables,
    table_data_api,
    table_update_api,
)

# Section management operations
from .section_management import (
    section_create_view,
    section_delete_view,
    section_toggle_exclude_view,
    section_move_up_view,
    section_move_down_view,
)


__all__ = [
    # Content operations
    "section_view",
    "save_sections_view",
    "section_history_view",
    "section_diff_view",
    "section_checkout_view",
    "section_commit_view",
    "read_tex_file_view",
    "available_sections_view",
    "presence_update_view",
    # Compilation operations
    "compile_api",
    "compilation_status_api",
    "compile_full_view",
    "compilation_job_status",
    "compile_preview_view",
    "compile_view",
    "preview_pdf_view",
    # Metadata operations
    "sections_config_view",
    "citations_api",
    "regenerate_bibliography_api",
    "file_tree_view",
    # File operations
    "pdf_view",
    "presence_list_view",
    "thumbnail_view",
    # Media operations
    "figures_api",
    "tables_api",
    "refresh_figures_index",
    "refresh_tables_index",
    "upload_figures",
    "upload_tables",
    "table_data_api",
    "table_update_api",
    # Section management operations
    "section_create_view",
    "section_delete_view",
    "section_toggle_exclude_view",
    "section_move_up_view",
    "section_move_down_view",
]

# EOF
