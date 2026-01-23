#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 04:54:30 (ywatanabe)"

"""
Project app signals - Refactored into modular structure.

This package provides Django signals for the project_app, including:
- Gitea repository creation and deletion
- Project initialization (cloning, writer structure, bibliography)
- Visibility synchronization between Django and Gitea

For backward compatibility, all signal handlers are imported and registered here.
"""

# Import signal handlers to register them
from .gitea_repository import create_gitea_repository, delete_gitea_repository
from .project_initialization import ensure_bibliography_structure
from .visibility_sync import track_visibility_change, sync_project_visibility

__all__ = [
    "create_gitea_repository",
    "delete_gitea_repository",
    "ensure_bibliography_structure",
    "track_visibility_change",
    "sync_project_visibility",
]

# EOF
