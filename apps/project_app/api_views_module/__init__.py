"""
Views module for project_app
Note: Main views are in views.py (sibling file), this directory only contains API views
"""
# The main views.py file exists as a sibling, not in this directory
# This __init__.py just provides API views as a module

from .api_views import (
    api_project_fork,
    api_project_star,
    api_project_stats,
    api_project_watch,
    api_switch_branch,
    get_current_branch_from_session,
)

__all__ = [
    "api_project_fork",
    "api_project_star",
    "api_project_stats",
    "api_project_watch",
    "api_switch_branch",
    "get_current_branch_from_session",
]
