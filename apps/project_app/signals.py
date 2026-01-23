#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 04:54:30 (ywatanabe)"

"""
Backward compatibility wrapper for project_app signals.

This file maintains backward compatibility by importing all signals from
the refactored signals package.

All signal handlers have been moved to:
- signals/gitea_repository.py - Gitea repository creation/deletion
- signals/project_initialization.py - Project cloning and setup
- signals/project_init_helpers.py - Helper utilities for initialization
- signals/visibility_sync.py - Visibility synchronization

The signals/__init__.py file imports and registers all handlers.
"""

# Import all signals from the refactored signals package for backward compatibility
from .signals import (
    create_gitea_repository,
    delete_gitea_repository,
    ensure_bibliography_structure,
    track_visibility_change,
    sync_project_visibility,
)

__all__ = [
    "create_gitea_repository",
    "delete_gitea_repository",
    "ensure_bibliography_structure",
    "track_visibility_change",
    "sync_project_visibility",
]

# EOF
