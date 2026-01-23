#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 14:46:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/code_app/services/singularity_manager/manager.py
# ----------------------------------------
from __future__ import annotations

__FILE__ = "./apps/code_app/services/singularity_manager/manager.py"
# ----------------------------------------

"""
Singularity Container Manager

Main manager class coordinating all Singularity operations.
Superior security alternative to Docker for user code execution.

Security Benefits:
- No root daemon required
- No Docker socket mounting
- User runs as themselves (UID preserved)
- Designed for multi-user HPC environments
"""

import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from django.contrib.auth.models import User

from .config import SingularityConfig
from .resource_manager import ResourceManager
from .cgroup_manager import CGroupManager
from .stats_manager import StatsManager
from .executor import SingularityExecutor
from .hpc_manager import HPCManager

logger = logging.getLogger(__name__)


class SingularityManager:
    """
    Manage Singularity containers for user code execution

    This provides a secure alternative to Docker with:
    - No daemon requirement
    - UID preservation (no mapping complexity)
    - HPC integration (SLURM, PBS)
    - Resource efficiency (single shared image)
    """

    def __init__(self):
        # Initialize configuration
        self.config = SingularityConfig()

        # Initialize component managers
        self.resource_manager = ResourceManager(self.config)
        self.cgroup_manager = CGroupManager(self.config)
        self.stats_manager = StatsManager(self.config)
        self.executor = SingularityExecutor(
            self.config,
            self.resource_manager,
            self.cgroup_manager,
            self.stats_manager
        )
        self.hpc_manager = HPCManager(self.config)

    # Resource management methods
    def get_active_job_count(self) -> int:
        """Get current number of active Singularity jobs"""
        return self.resource_manager.get_active_job_count()

    def can_execute(self) -> Tuple[bool, str]:
        """
        Check if resources are available for execution

        Returns:
            (can_execute, reason)
        """
        return self.resource_manager.can_execute()

    # Execution methods
    def execute_code(
        self,
        user: User,
        script_path: Path,
        timeout: Optional[int] = None,
        bind_workspace: bool = True,
        capture_output: bool = True
    ) -> Dict[str, Any]:
        """
        Execute user code in Singularity container

        Args:
            user: Django user object
            script_path: Path to Python script to execute
            timeout: Execution timeout in seconds (None = default)
            bind_workspace: Whether to bind user workspace directory
            capture_output: Whether to capture stdout/stderr

        Returns:
            Dict with stdout, stderr, returncode, execution_time

        Security Features:
            - No root daemon required
            - Runs as invoking user (preserves UID)
            - Isolated /tmp and /var/tmp (--contain)
            - Clean environment variables (--cleanenv)
            - No home directory mounted (--no-home)
            - Resource limits via cgroups

        Raises:
            ResourceWarning: If resources unavailable
            SingularityError: On execution errors
        """
        return self.executor.execute_code(
            user,
            script_path,
            timeout,
            bind_workspace,
            capture_output
        )

    # Statistics methods
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get execution statistics for a user"""
        return self.stats_manager.get_user_stats(user_id)

    # HPC methods
    def submit_to_hpc(
        self,
        user: User,
        script_path: Path,
        hpc_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Submit job to HPC cluster (e.g., Spartan) via SLURM

        Args:
            user: Django user object
            script_path: Path to Python script
            hpc_config: HPC configuration (partition, time, cpus, mem)

        Returns:
            SLURM job ID

        Raises:
            SingularityError: On submission failure
        """
        return self.hpc_manager.submit_to_hpc(user, script_path, hpc_config)

    def get_hpc_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get SLURM job status

        Args:
            job_id: SLURM job ID

        Returns:
            Dict with status, runtime, node
        """
        return self.hpc_manager.get_hpc_job_status(job_id)


# EOF
