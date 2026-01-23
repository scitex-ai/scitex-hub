"""
SciTeX Cloud - Project Filesystem Management Module

This module provides filesystem operations for managing user and project directories
in SciTeX Cloud. It handles project directory structures, file storage, execution
tracking, and template-based project initialization.

Public API:
-----------
- ProjectFilesystemManager: Core manager class for filesystem operations
- get_project_filesystem_manager: Factory function to get/create manager instance
- ensure_project_directory: Utility to ensure project has directory structure

Usage:
------
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
        ensure_project_directory
    )

    # Get manager for a user
    manager = get_project_filesystem_manager(user)

    # Ensure project has directory
    ensure_project_directory(project)

Module Structure:
-----------------
- core.py: Core ProjectFilesystemManager class and initialization
- manager.py: ProjectOpsManager with integrated operations
- file_ops.py: File storage and listing operations
- execution_ops.py: Script execution tracking with RUNNING/FINISHED markers
- template_ops.py: Template copying and customization logic
- git_ops.py: Git repository cloning and integration
"""

# Import the unified manager class
from .manager import (
    ProjectOpsManager,
    get_project_filesystem_manager,
    ensure_project_directory,
)

# For backward compatibility, export as ProjectFilesystemManager
ProjectFilesystemManager = ProjectOpsManager

# Define public API
__all__ = [
    "ProjectFilesystemManager",
    "get_project_filesystem_manager",
    "ensure_project_directory",
]
