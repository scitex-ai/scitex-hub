"""
GitHub Integration Views
Modular organization of GitHub-related views for SciTeX Cloud
"""

# OAuth and Authentication
from .oauth import (
    github_oauth_initiate,
    github_oauth_callback,
)

# Repository Management
from .repositories import (
    github_create_repository,
    github_link_repository,
    github_list_repositories,
)

# Status and Sync
from .status import (
    github_get_status,
    github_sync_status,
)

# Git Operations
from .operations import (
    github_commit_files,
    github_push_changes,
)

__all__ = [
    # OAuth
    "github_oauth_initiate",
    "github_oauth_callback",
    # Repositories
    "github_create_repository",
    "github_link_repository",
    "github_list_repositories",
    # Status
    "github_get_status",
    "github_sync_status",
    # Operations
    "github_commit_files",
    "github_push_changes",
]
