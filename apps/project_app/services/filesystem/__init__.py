"""
SciTeX Cloud - User Directory Management System

This module handles user-specific directory trees with a minimal structure.

Minimal Directory Structure:
./data/users/{username}/
├── {project-slug}/                 # Project directories (1:1 with Django Project + Gitea repo)
│   ├── .git/                       # Git repository
│   ├── README.md
│   ├── scitex/                     # (Optional) SciTeX-specific project metadata
│   │   ├── scholar/                # Bibliography, enriched BibTeX files
│   │   ├── writer/                 # LaTeX compilation artifacts
│   │   ├── code/                   # Analysis tracking
│   │   └── viz/                    # Visualization outputs
│   └── ...                         # User's project structure
└── workspace_info.json             # User workspace metadata

Design Philosophy:
- Projects are self-contained Git repositories
- SciTeX features use project-slug/scitex/ subdirectory (created on-demand)
- No global shared/temp directories - keeps things simple
- Future expansions go under scitex/ to avoid namespace conflicts
"""

# Main manager class
from .manager import (
    ProjectFilesystemManager,
    get_project_filesystem_manager,
    ensure_project_directory,
)

# Path utilities
from .paths import (
    get_user_base_path,
    get_project_root_path,
    ensure_directory,
    get_file_extension,
    get_subcategory,
)

# Operations
from .operations import (
    store_document,
    store_file,
    list_project_files,
    get_project_structure,
    delete_project_directory,
    get_storage_usage,
)

# Git operations
from .git_operations import (
    clone_from_git,
    get_script_executions,
)

# Permission checks
from .permissions import (
    can_access_project,
    can_modify_project,
    can_delete_project,
    validate_path_in_project,
)

__all__ = [
    # Main classes
    "ProjectFilesystemManager",
    "get_project_filesystem_manager",
    "ensure_project_directory",
    # Path utilities
    "get_user_base_path",
    "get_project_root_path",
    "ensure_directory",
    "get_file_extension",
    "get_subcategory",
    # Operations
    "store_document",
    "store_file",
    "list_project_files",
    "get_project_structure",
    "delete_project_directory",
    "get_storage_usage",
    # Git operations
    "clone_from_git",
    "get_script_executions",
    # Permissions
    "can_access_project",
    "can_modify_project",
    "can_delete_project",
    "validate_path_in_project",
]
