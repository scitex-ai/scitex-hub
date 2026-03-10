"""
Gitea App Views
Main views module with backward-compatible imports
"""

# GitHub Integration Views (backward compatibility)
from .github import (
    github_commit_files,
    github_create_repository,
    github_get_status,
    github_link_repository,
    github_list_repositories,
    github_oauth_callback,
    github_oauth_initiate,
    github_push_changes,
    github_sync_status,
)

# Gitea → Django sync webhook
from .webhook_sync import gitea_sync_webhook

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
    # Gitea sync webhook
    "gitea_sync_webhook",
]
