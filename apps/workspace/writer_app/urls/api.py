#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04 20:52:01 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/urls/api.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/writer_app/urls/api.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------
"""
Writer App API URLs

REST API endpoints for writer operations:
- Section read/write
- Compilation (preview & full)
- Git operations
- Presence tracking
- File operations
"""

from django.urls import path

from ..views.editor import ai2_prompt
from ..views.editor import api as api_views
from ..views.git import api as git_api
from ..views.index import main as index_views

urlpatterns = [
    # Workspace initialization
    path(
        "initialize-workspace/",
        index_views.initialize_workspace,
        name="api_initialize_workspace",
    ),
    # Sections config (no project_id needed)
    path(
        "sections-config/", api_views.sections_config_view, name="api_sections_config"
    ),
    # Section management operations (MUST come BEFORE general section pattern)
    path(
        "project/<int:project_id>/section/create/",
        api_views.section_create_view,
        name="api_section_create",
    ),
    path(
        "project/<int:project_id>/section/<path:section_name>/delete/",
        api_views.section_delete_view,
        name="api_section_delete",
    ),
    path(
        "project/<int:project_id>/section/<path:section_name>/toggle-exclude/",
        api_views.section_toggle_exclude_view,
        name="api_section_toggle_exclude",
    ),
    path(
        "project/<int:project_id>/section/<path:section_name>/move-up/",
        api_views.section_move_up_view,
        name="api_section_move_up",
    ),
    path(
        "project/<int:project_id>/section/<path:section_name>/move-down/",
        api_views.section_move_down_view,
        name="api_section_move_down",
    ),
    # Section CRUD operations (supports hierarchical IDs like "shared/authors")
    # This MUST come AFTER specific endpoints to avoid catching their URLs
    path(
        "project/<int:project_id>/section/<path:section_name>/",
        api_views.section_view,
        name="api_section",
    ),
    # Compilation
    path(
        "project/<int:project_id>/compile_preview/",
        api_views.compile_preview_view,
        name="api_compile_preview",
    ),
    path(
        "project/<int:project_id>/compile_full/",
        api_views.compile_full_view,
        name="api_compile_full",
    ),
    path(
        "project/<int:project_id>/compilation/status/<str:job_id>/",
        api_views.compilation_job_status,
        name="api_compilation_status",
    ),
    path(
        "project/<int:project_id>/compile/",
        api_views.compile_view,
        name="api_compile",
    ),
    # Git operations - Section-specific (scitex.writer git)
    path(
        "project/<int:project_id>/section/<str:section_name>/history/",
        api_views.section_history_view,
        name="api_section_history",
    ),
    path(
        "project/<int:project_id>/section/<str:section_name>/diff/",
        api_views.section_diff_view,
        name="api_section_diff",
    ),
    path(
        "project/<int:project_id>/section/<str:section_name>/checkout/",
        api_views.section_checkout_view,
        name="api_section_checkout",
    ),
    path(
        "project/<int:project_id>/section/<str:section_name>/commit/",
        api_views.section_commit_view,
        name="api_section_commit",
    ),
    # Git operations - Workspace-level (GitPython direct access)
    path(
        "project/<int:project_id>/git/history/",
        git_api.git_history_api,
        name="api_git_history",
    ),
    path(
        "project/<int:project_id>/git/diff/",
        git_api.git_diff_api,
        name="api_git_diff",
    ),
    path(
        "project/<int:project_id>/git/status/",
        git_api.git_status_api,
        name="api_git_status",
    ),
    path(
        "project/<int:project_id>/git/branches/",
        git_api.git_branches_api,
        name="api_git_branches",
    ),
    path(
        "project/<int:project_id>/git/branch/create/",
        git_api.git_create_branch_api,
        name="api_git_create_branch",
    ),
    path(
        "project/<int:project_id>/git/branch/switch/",
        git_api.git_switch_branch_api,
        name="api_git_switch_branch",
    ),
    path(
        "project/<int:project_id>/git/commit/",
        git_api.git_commit_api,
        name="api_git_commit",
    ),
    # PDF and file operations (accept optional trailing slash)
    path(
        "project/<int:project_id>/pdf/<str:pdf_filename>/",
        api_views.pdf_view,
        name="api_pdf_file_slash",
    ),
    path(
        "project/<int:project_id>/pdf/<str:pdf_filename>",
        api_views.pdf_view,
        name="api_pdf_file",
    ),
    path("project/<int:project_id>/pdf/", api_views.pdf_view, name="api_pdf"),
    path(
        "project/<int:project_id>/preview-pdf/",
        api_views.preview_pdf_view,
        name="api_preview_pdf",
    ),
    path(
        "project/<int:project_id>/file-tree/",
        api_views.file_tree_view,
        name="api_file_tree",
    ),
    path(
        "project/<int:project_id>/read-tex-file/",
        api_views.read_tex_file_view,
        name="api_read_tex_file",
    ),
    # Section management
    path(
        "project/<int:project_id>/available-sections/",
        api_views.available_sections_view,
        name="api_available_sections",
    ),
    path(
        "project/<int:project_id>/save-sections/",
        api_views.save_sections_view,
        name="api_save_sections",
    ),
    # Presence tracking
    path(
        "project/<int:project_id>/presence/update/",
        api_views.presence_update_view,
        name="api_presence_update",
    ),
    path(
        "project/<int:project_id>/presence/list/",
        api_views.presence_list_view,
        name="api_presence_list",
    ),
    # Citations (for autocomplete)
    path(
        "project/<int:project_id>/citations/",
        api_views.citations_api,
        name="api_citations",
    ),
    # Figures management
    path(
        "project/<int:project_id>/figures/",
        api_views.figures_api,
        name="api_figures",
    ),
    path(
        "project/<int:project_id>/figures/refresh/",
        api_views.refresh_figures_index,
        name="api_figures_refresh",
    ),
    path(
        "project/<int:project_id>/upload-figures/",
        api_views.upload_figures,
        name="api_upload_figures",
    ),
    path(
        "project/<int:project_id>/thumbnail/<str:thumbnail_name>",
        api_views.thumbnail_view,
        name="api_thumbnail",
    ),
    # Tables management
    path(
        "project/<int:project_id>/tables/",
        api_views.tables_api,
        name="api_tables",
    ),
    path(
        "project/<int:project_id>/tables/refresh/",
        api_views.refresh_tables_index,
        name="api_tables_refresh",
    ),
    path(
        "project/<int:project_id>/upload-tables/",
        api_views.upload_tables,
        name="api_upload_tables",
    ),
    path(
        "project/<int:project_id>/table-data/<str:file_hash>/",
        api_views.table_data_api,
        name="api_table_data",
    ),
    path(
        "project/<int:project_id>/table-update/<str:file_hash>/",
        api_views.table_update_api,
        name="api_table_update",
    ),
    # SyncTeX reverse lookup (PDF click -> TeX source)
    path(
        "project/<int:project_id>/synctex/",
        api_views.synctex_reverse_lookup,
        name="api_synctex_reverse_lookup",
    ),
    # Bibliography upload and regeneration
    path(
        "project/<int:project_id>/upload-bibliography/",
        api_views.upload_bibliography,
        name="api_upload_bibliography",
    ),
    path(
        "project/<int:project_id>/regenerate-bibliography/",
        api_views.regenerate_bibliography_api,
        name="api_regenerate_bibliography",
    ),
    # AI2 Asta prompt generation
    path(
        "project/<int:project_id>/generate-ai2-prompt/",
        ai2_prompt.generate_asta_view,
        name="api_generate_ai2_prompt",
    ),
]

# EOF
