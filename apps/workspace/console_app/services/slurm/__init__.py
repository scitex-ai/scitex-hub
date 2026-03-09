#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLURM job management for SciTeX Cloud.

This module provides a Python interface to SLURM for submitting and managing
computational jobs in Apptainer containers.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from .job_operations import cancel_job, get_job_output, get_job_status, submit_job
from .queue_operations import get_queue_status, is_slurm_available, list_jobs

logger = logging.getLogger(__name__)


class SlurmManager:
    """
    Manage SLURM job submissions for SciTeX Cloud.

    Handles job submission, status monitoring, and cancellation through
    SLURM's command-line interface.
    """

    def __init__(self, job_scripts_dir: Optional[Path] = None):
        """
        Initialize SLURM manager.

        Args:
            job_scripts_dir: Directory to store generated batch scripts.
                           Defaults to /app/data/slurm/scripts in production,
                           or /tmp/slurm/scripts in development.
        """
        if job_scripts_dir is None:
            # Use /tmp for development, /app for production
            if Path("/app").exists():
                job_scripts_dir = Path("/app/data/slurm/scripts")
            else:
                job_scripts_dir = Path("/tmp/slurm/scripts")

        self.job_scripts_dir = Path(job_scripts_dir)
        self.job_scripts_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"SlurmManager initialized with scripts dir: {self.job_scripts_dir}"
        )

    def submit_job(
        self,
        user_id: str,
        script_path: Path,
        container_path: Path,
        workspace: Path,
        job_name: str = "scitex_job",
        partition: str = "normal",
        cpus: int = 1,
        memory_gb: int = 4,
        time_limit: str = "01:00:00",
        env_vars: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """Submit a job to SLURM."""
        return submit_job(
            job_scripts_dir=self.job_scripts_dir,
            user_id=user_id,
            script_path=script_path,
            container_path=container_path,
            workspace=workspace,
            job_name=job_name,
            partition=partition,
            cpus=cpus,
            memory_gb=memory_gb,
            time_limit=time_limit,
            env_vars=env_vars,
        )

    def get_job_status(self, job_id: int) -> Dict:
        """Get status of a SLURM job."""
        return get_job_status(job_id)

    def cancel_job(self, job_id: int) -> Dict:
        """Cancel a SLURM job."""
        return cancel_job(job_id)

    def get_queue_status(self) -> Dict:
        """Get overall cluster/queue status."""
        return get_queue_status()

    def list_jobs(
        self, user: Optional[str] = None, state: Optional[str] = None
    ) -> Dict:
        """List SLURM jobs with detailed information."""
        return list_jobs(user=user, state=state)

    def is_available(self) -> bool:
        """Check if SLURM is available on this system."""
        return is_slurm_available()

    def get_job_output(
        self, job_id: int, workspace: Path, tail_lines: int = 100
    ) -> Dict:
        """Get job output logs."""
        return get_job_output(job_id, workspace, tail_lines)


__all__ = ["SlurmManager"]


# EOF
