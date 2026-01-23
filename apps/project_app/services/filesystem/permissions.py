"""
Permission checks for project filesystem operations.

This module handles all permission-related validation.
"""

from pathlib import Path
from typing import Optional
from django.contrib.auth.models import User
from ...models import Project


def can_access_project(user: User, project: Project) -> bool:
    """Check if user has access to a project."""
    return project.owner == user or user in project.collaborators.all()


def can_modify_project(user: User, project: Project) -> bool:
    """Check if user can modify a project."""
    return project.owner == user


def can_delete_project(user: User, project: Project) -> bool:
    """Check if user can delete a project."""
    return project.owner == user


def validate_path_in_project(project_path: Path, target_path: Path) -> bool:
    """
    Validate that a path is within the project directory.

    This prevents path traversal attacks.
    """
    try:
        target_path.resolve().relative_to(project_path.resolve())
        return True
    except ValueError:
        return False
