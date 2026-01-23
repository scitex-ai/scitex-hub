#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project-specific SQLite database for figures/tables metadata.

This module provides fast, portable indexing of media files in SciTeX projects.
The database is stored in scitex/metadata.db within each project directory.
"""

from .core import ProjectDatabase
from .utils import get_project_db

__all__ = [
    'ProjectDatabase',
    'get_project_db',
]

# EOF
