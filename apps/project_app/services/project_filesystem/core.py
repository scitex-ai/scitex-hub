"""
SciTeX Cloud - Project Filesystem Core Module

This module contains the core ProjectFilesystemManager class definition,
initialization logic, and base path management.

Extracted from project_filesystem.py for better maintainability.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict

from django.conf import settings
from django.contrib.auth.models import User


class ProjectFilesystemManager:
    """Manages user-specific directory structures for SciTeX Cloud."""

    # Standardized scientific research project structure
    PROJECT_STRUCTURE = {
        "config": [],  # Configuration files (YAML, JSON, etc.)
        "data": {
            "raw": [],  # Raw datasets
            "processed": [],  # Processed/cleaned data
            "figures": [],  # Generated figures and plots
            "models": [],  # Trained models
        },
        "scripts": [],  # Main scripts directory (will contain project-specific subdirs)
        "docs": ["manuscripts", "notes", "references"],  # Documentation
        "results": ["outputs", "reports", "analysis"],  # Results and analysis
        "temp": ["cache", "logs", "tmp"],  # Temporary files
    }

    def __init__(self, user: User):
        """
        Initialize ProjectFilesystemManager for a user.

        Args:
            user: Django User instance
        """
        self.user = user
        self.base_path = self._get_user_base_path()

    def _get_user_base_path(self) -> Path:
        """
        Get the base directory path for the user.

        Structure: ./data/users/{username}/proj/
        All projects go under the proj subdirectory.

        Returns:
            Path object representing the user's base directory
        """
        return Path(settings.BASE_DIR) / "data" / "users" / self.user.username / "proj"

    def _ensure_directory(self, path: Path) -> bool:
        """
        Ensure a directory exists, create if it doesn't.

        Args:
            path: Directory path to ensure exists

        Returns:
            True if directory exists or was created successfully, False otherwise
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directory {path}: {e}")
            return False

    def initialize_user_workspace(self) -> bool:
        """
        Initialize minimal user workspace - just the base directory.

        Creates:
        - Base user directory (./data/users/{username}/proj/)
        - workspace_info.json with user metadata

        Returns:
            True if workspace was initialized successfully, False otherwise
        """
        try:
            # Create base user directory only
            # Projects will be created directly under this directory
            if not self._ensure_directory(self.base_path):
                return False

            # Create user workspace info file
            self._create_workspace_info()

            return True
        except Exception as e:
            print(f"Error initializing user workspace: {e}")
            return False

    def _create_workspace_info(self):
        """
        Create workspace information file.

        Creates workspace_info.json with:
        - user_id: Django user ID
        - username: User's username
        - created_at: ISO format timestamp
        - version: Workspace version
        - structure_version: Directory structure version
        """
        info = {
            "user_id": self.user.id,
            "username": self.user.username,
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
            "structure_version": "1.0",
        }

        info_path = self.base_path / "workspace_info.json"
        with open(info_path, "w") as f:
            json.dump(info, f, indent=2)


def get_project_filesystem_manager(user: User) -> ProjectFilesystemManager:
    """
    Get or create a ProjectFilesystemManager for the user.

    Initializes workspace if it doesn't exist.

    Args:
        user: Django User instance

    Returns:
        ProjectFilesystemManager instance for the user
    """
    manager = ProjectFilesystemManager(user)

    # Initialize workspace if it doesn't exist
    if not manager.base_path.exists():
        manager.initialize_user_workspace()

    return manager
