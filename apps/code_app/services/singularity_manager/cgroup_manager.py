#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 14:46:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/code_app/services/singularity_manager/cgroup_manager.py
# ----------------------------------------
from __future__ import annotations

__FILE__ = "./apps/code_app/services/singularity_manager/cgroup_manager.py"
# ----------------------------------------

"""
Singularity CGroup Manager

Resource limits management using cgroups.
"""

from pathlib import Path
from django.conf import settings


class CGroupManager:
    """
    Manage cgroup resource limits for containers

    Handles:
    - CPU limits
    - Memory limits
    - Process limits
    - CGroup configuration file generation
    """

    def __init__(self, config):
        """
        Initialize cgroup manager

        Args:
            config: SingularityConfig instance
        """
        self.config = config

    def create_cgroup_config(self, user_id: int) -> Path:
        """
        Create cgroup configuration file for resource limits

        Resource Limits (aligned with NAS allocation):
        - CPU: 0.35 cores (35% of 1 core)
        - Memory: 2GB
        - PIDs: 256 processes (prevent fork bombs)

        Args:
            user_id: User ID for unique config file

        Returns:
            Path to cgroup config file
        """
        cgroup_dir = Path(settings.MEDIA_ROOT) / "cgroups"
        cgroup_dir.mkdir(parents=True, exist_ok=True)

        cgroup_file = cgroup_dir / f"user_{user_id}.toml"

        # Singularity cgroup config format (TOML)
        # See: https://sylabs.io/guides/3.8/user-guide/cgroups.html
        config = """# Singularity cgroup configuration for user workspace
# Generated automatically - do not edit manually

[cpu]
    # CPU shares: 350 = 35% of 1 core (out of 1024)
    shares = 350

[memory]
    # Memory limit: 2GB in bytes
    limit = 2147483648
    # Swap limit: same as memory (no swap)
    swap = 2147483648

[pids]
    # Process limit: prevent fork bombs
    limit = 256
"""

        cgroup_file.write_text(config)
        return cgroup_file


# EOF
