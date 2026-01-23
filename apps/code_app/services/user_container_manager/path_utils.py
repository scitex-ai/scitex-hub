#!/usr/bin/env python3
"""
Path utilities for User Container Manager
"""

from pathlib import Path
from django.contrib.auth.models import User


class PathUtils:
    """Utilities for managing container paths"""

    def __init__(self, config):
        self.config = config

    def get_user_dir(self, user: User) -> Path:
        """Get user's container directory"""
        user_dir = self.config.user_containers_dir / str(user.id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def get_user_container_path(self, user: User) -> Path:
        """Get path to user's custom container"""
        return self.get_user_dir(user) / "custom.sif"

    def get_sandbox_path(self, user: User) -> Path:
        """Get path to user's sandbox (writable directory)"""
        return self.get_user_dir(user) / "sandbox"

    def has_custom_container(self, user: User) -> bool:
        """Check if user has custom container"""
        return self.get_user_container_path(user).exists()

    def get_active_container(self, user: User) -> Path:
        """
        Get container to use for execution (custom or base)

        Returns:
            Path to .sif file
        """
        custom = self.get_user_container_path(user)
        return custom if custom.exists() else self.config.base_image

# EOF
