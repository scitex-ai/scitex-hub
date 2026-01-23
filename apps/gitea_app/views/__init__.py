"""
Gitea App Views
Main views module with backward-compatible imports
"""

# GitHub Integration Views (backward compatibility)
from .github import (
    github_oauth_initiate,
    github_oauth_callback,
    github_create_repository,
    github_link_repository,
    github_list_repositories,
    github_get_status,
    github_sync_status,
    github_commit_files,
    github_push_changes,
)

__all__ = [
    # GitHub OAuth
    "github_oauth_initiate",
    "github_oauth_callback",
    # GitHub Repositories
    "github_create_repository",
    "github_link_repository",
    "github_list_repositories",
    # GitHub Status
    "github_get_status",
    "github_sync_status",
    # GitHub Operations
    "github_commit_files",
    "github_push_changes",
]
