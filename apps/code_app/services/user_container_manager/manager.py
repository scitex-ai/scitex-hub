#!/usr/bin/env python3
"""
Main User Container Manager
Orchestrates all container operations
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from django.contrib.auth.models import User

from .config import ContainerConfig
from .path_utils import PathUtils
from .stats import StatsManager
from .container_ops import ContainerOperations
from .package_ops import PackageOperations


class UserContainerManager:
    """
    Manage user-customizable Apptainer/Singularity containers

    Allows users to:
    - Build custom containers from the base image
    - Install packages (apt, pip, conda)
    - Use fakeroot for rootless building
    - Stay within storage quotas
    """

    def __init__(self):
        # Initialize configuration
        self.config = ContainerConfig()

        # Initialize utilities
        self.path_utils = PathUtils(self.config)
        self.stats_manager = StatsManager(self.config, self.path_utils)

        # Initialize operations
        self.container_ops = ContainerOperations(
            self.config, self.path_utils, self.stats_manager
        )
        self.package_ops = PackageOperations(self.config, self.path_utils)

    # Expose configuration properties
    @property
    def base_image(self) -> Path:
        return self.config.base_image

    @property
    def user_containers_dir(self) -> Path:
        return self.config.user_containers_dir

    @property
    def max_container_size(self) -> int:
        return self.config.max_container_size

    @property
    def max_build_time(self) -> int:
        return self.config.max_build_time

    @property
    def max_builds_per_day(self) -> int:
        return self.config.max_builds_per_day

    @property
    def container_cmd(self) -> str:
        return self.config.container_cmd

    @property
    def cache_prefix(self) -> str:
        return self.config.cache_prefix

    # Delegate path utilities
    def get_user_dir(self, user: User) -> Path:
        """Get user's container directory"""
        return self.path_utils.get_user_dir(user)

    def get_user_container_path(self, user: User) -> Path:
        """Get path to user's custom container"""
        return self.path_utils.get_user_container_path(user)

    def get_sandbox_path(self, user: User) -> Path:
        """Get path to user's sandbox (writable directory)"""
        return self.path_utils.get_sandbox_path(user)

    def has_custom_container(self, user: User) -> bool:
        """Check if user has custom container"""
        return self.path_utils.has_custom_container(user)

    def get_active_container(self, user: User) -> Path:
        """Get container to use for execution (custom or base)"""
        return self.path_utils.get_active_container(user)

    # Delegate statistics
    def get_container_stats(self, user: User) -> Dict[str, Any]:
        """Get user's container statistics"""
        return self.stats_manager.get_container_stats(user)

    # Delegate container operations
    def create_sandbox(self, user: User) -> Dict[str, Any]:
        """Create writable sandbox for user to customize"""
        return self.container_ops.create_sandbox(user)

    def finalize_sandbox(self, user: User) -> Dict[str, Any]:
        """Convert sandbox to final .sif container"""
        return self.container_ops.finalize_sandbox(user)

    def build_from_definition(
        self,
        user: User,
        definition_content: str
    ) -> Dict[str, Any]:
        """Build custom container from user's definition file"""
        return self.container_ops.build_from_definition(user, definition_content)

    def delete_custom_container(self, user: User) -> Dict[str, Any]:
        """Delete user's custom container and sandbox"""
        return self.container_ops.delete_custom_container(user)

    # Delegate package operations
    def install_package(
        self,
        user: User,
        package_manager: str,
        packages: List[str]
    ) -> Dict[str, Any]:
        """Install packages to user's sandbox"""
        return self.package_ops.install_package(user, package_manager, packages)

    # Additional utilities
    def _check_fakeroot_available(self) -> bool:
        """Check if fakeroot is available for this user"""
        return self.config.check_fakeroot_available()

    def _check_build_rate_limit(self, user: User) -> tuple[bool, str]:
        """Check if user has exceeded build rate limit"""
        return self.stats_manager.check_build_rate_limit(user)

    def _increment_build_count(self, user: User):
        """Increment user's build count for today"""
        return self.stats_manager.increment_build_count(user)

# EOF
