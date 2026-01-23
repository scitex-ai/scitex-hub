#!/usr/bin/env python3
"""
Configuration and initialization for User Container Manager
"""

import subprocess
import logging
from pathlib import Path
from django.conf import settings
from .exceptions import UserContainerError

logger = logging.getLogger(__name__)


class ContainerConfig:
    """
    Configuration for user container management

    Handles:
    - Path configuration
    - Limits and quotas
    - Container command detection
    """

    def __init__(self):
        # Configuration from Django settings
        self.base_image = Path(settings.SINGULARITY_IMAGE_PATH)
        self.user_containers_dir = Path(settings.MEDIA_ROOT) / "user_containers"
        self.user_containers_dir.mkdir(parents=True, exist_ok=True)

        # Limits
        self.max_container_size = settings.USER_CONTAINER_MAX_SIZE_GB * 1024**3  # Convert to bytes
        self.max_build_time = settings.USER_CONTAINER_MAX_BUILD_TIME
        self.max_builds_per_day = settings.USER_CONTAINER_MAX_BUILDS_PER_DAY

        # Detect Apptainer vs Singularity
        self.container_cmd = self._detect_container_command()

        # Cache key prefix
        self.cache_prefix = 'user_container_'

    def _detect_container_command(self) -> str:
        """
        Detect whether to use 'apptainer' or 'singularity' command

        Returns:
            'apptainer' or 'singularity'
        """
        # Try apptainer first (newer)
        try:
            result = subprocess.run(
                ["apptainer", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("Using 'apptainer' command")
                return "apptainer"
        except FileNotFoundError:
            pass

        # Fall back to singularity
        try:
            result = subprocess.run(
                ["singularity", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("Using 'singularity' command")
                return "singularity"
        except FileNotFoundError:
            pass

        raise UserContainerError(
            "Neither 'apptainer' nor 'singularity' command found. "
            "Install with: sudo apt-get install apptainer"
        )

    def check_fakeroot_available(self) -> bool:
        """Check if fakeroot is available for this user"""
        try:
            result = subprocess.run(
                [self.container_cmd, "exec", "--fakeroot", str(self.base_image), "true"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Fakeroot check failed: {e}")
            return False

# EOF
