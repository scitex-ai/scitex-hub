#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Project API views package.

Re-exports all API endpoint functions for URL routing.
"""

from __future__ import annotations

from .branch import api_switch_branch, get_current_branch_from_session
from .social import (
    api_project_fork,
    api_project_star,
    api_project_stats,
    api_project_watch,
)

__all__ = [
    "api_project_fork",
    "api_project_star",
    "api_project_stats",
    "api_project_watch",
    "api_switch_branch",
    "get_current_branch_from_session",
]


# EOF
