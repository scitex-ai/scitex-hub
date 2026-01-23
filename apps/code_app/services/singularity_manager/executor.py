#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 14:46:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/code_app/services/singularity_manager/executor.py
# ----------------------------------------
from __future__ import annotations

__FILE__ = "./apps/code_app/services/singularity_manager/executor.py"
# ----------------------------------------

"""
Singularity Executor

Code execution in Singularity containers with security and resource management.
"""

import subprocess
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
from django.conf import settings
from django.contrib.auth.models import User

from .exceptions import SingularityError

logger = logging.getLogger(__name__)


class SingularityExecutor:
    """
    Execute user code in Singularity containers

    Handles:
    - Secure code execution
    - Workspace binding
    - Resource limits
    - Timeout management
    - Output capture
    """

    def __init__(self, config, resource_manager, cgroup_manager, stats_manager):
        """
        Initialize executor

        Args:
            config: SingularityConfig instance
            resource_manager: ResourceManager instance
            cgroup_manager: CGroupManager instance
            stats_manager: StatsManager instance
        """
        self.config = config
        self.resource_manager = resource_manager
        self.cgroup_manager = cgroup_manager
        self.stats_manager = stats_manager

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
        # Use default timeout if not specified
        if timeout is None:
            timeout = self.config.default_timeout
        elif timeout > self.config.max_timeout:
            logger.warning(
                f"Requested timeout {timeout}s exceeds max {self.config.max_timeout}s, capping"
            )
            timeout = self.config.max_timeout

        # Check resource availability
        can_run, reason = self.resource_manager.can_execute()
        if not can_run:
            raise ResourceWarning(f"Cannot execute: {reason}")

        # Prepare workspace binding
        workspace_dir = Path(settings.MEDIA_ROOT) / "users" / str(user.id) / "workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Verify script exists
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        # Build Singularity command with security options
        cmd = [
            "singularity", "exec",
            "--contain",     # Isolated /tmp, /var/tmp
            "--cleanenv",    # Clean environment
            "--no-home",     # Don't mount home directory
        ]

        # Bind workspace if requested
        if bind_workspace:
            cmd.extend([
                "--bind", f"{workspace_dir}:/workspace:rw",
                "--pwd", "/workspace",
            ])

        # Apply resource limits (cgroups)
        # Note: Requires Singularity 3.8+ and cgroups v2
        try:
            cgroup_config = self.cgroup_manager.create_cgroup_config(user.id)
            cmd.extend([
                "--apply-cgroups", str(cgroup_config),
            ])
        except Exception as e:
            logger.warning(f"Could not apply cgroups (running without limits): {e}")

        # Add image and command
        cmd.extend([
            str(self.config.image_path),
            "python", str(script_path)
        ])

        # Execute with timeout
        start_time = time.time()

        try:
            # Increment active job counter
            self.resource_manager._increment_job_count()

            logger.info(
                f"Executing Singularity job for user {user.username}: {script_path.name}"
            )
            logger.debug(f"Command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=False,
                cwd=workspace_dir,
            )

            execution_time = time.time() - start_time

            logger.info(
                f"Singularity job completed for user {user.username}: "
                f"exit_code={result.returncode}, duration={execution_time:.2f}s"
            )

            # Update statistics
            self.stats_manager.update_stats(user.id, execution_time, result.returncode == 0)

            return {
                'stdout': result.stdout if capture_output else '',
                'stderr': result.stderr if capture_output else '',
                'returncode': result.returncode,
                'execution_time': execution_time,
                'timeout': timeout,
                'success': result.returncode == 0,
            }

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            logger.warning(
                f"Singularity job timeout for user {user.username} after {timeout}s"
            )

            self.stats_manager.update_stats(user.id, execution_time, False)

            return {
                'stdout': '',
                'stderr': f'Execution timed out after {timeout} seconds',
                'returncode': -1,
                'execution_time': execution_time,
                'timeout': timeout,
                'success': False,
            }

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Singularity execution error for user {user.username}: {e}")

            self.stats_manager.update_stats(user.id, execution_time, False)

            return {
                'stdout': '',
                'stderr': f'Execution error: {str(e)}',
                'returncode': -1,
                'execution_time': execution_time,
                'timeout': timeout,
                'success': False,
            }

        finally:
            # Decrement active job counter
            self.resource_manager._decrement_job_count()


# EOF
