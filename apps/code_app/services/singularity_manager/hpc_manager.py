#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 14:46:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/code_app/services/singularity_manager/hpc_manager.py
# ----------------------------------------
from __future__ import annotations

__FILE__ = "./apps/code_app/services/singularity_manager/hpc_manager.py"
# ----------------------------------------

"""
Singularity HPC Manager

SLURM job submission and management for HPC clusters.
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from django.contrib.auth.models import User

from .exceptions import SingularityError

logger = logging.getLogger(__name__)


class HPCManager:
    """
    Manage HPC cluster job submission

    Handles:
    - SLURM job submission
    - Job status monitoring
    - HPC workspace configuration
    """

    def __init__(self, config):
        """
        Initialize HPC manager

        Args:
            config: SingularityConfig instance
        """
        self.config = config

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
        # Default HPC configuration
        if hpc_config is None:
            hpc_config = {
                'partition': 'compute',
                'time': '01:00:00',
                'cpus': 1,
                'mem': '4G',
            }

        # Prepare directories
        hpc_workspace = f"/data/projects/scitex/users/{user.id}/workspace"
        hpc_logs = f"/data/projects/scitex/users/{user.id}/logs"

        # Create SLURM submission script
        slurm_script = f"""#!/bin/bash
#SBATCH --job-name=scitex_{user.id}
#SBATCH --partition={hpc_config['partition']}
#SBATCH --time={hpc_config['time']}
#SBATCH --cpus-per-task={hpc_config['cpus']}
#SBATCH --mem={hpc_config['mem']}
#SBATCH --output={hpc_logs}/slurm-%j.out
#SBATCH --error={hpc_logs}/slurm-%j.err

# Load Singularity module (HPC-specific)
module load singularity/3.8.0

# Execute code in Singularity container
singularity exec \\
    --contain \\
    --cleanenv \\
    --bind {hpc_workspace}:/workspace \\
    --pwd /workspace \\
    /data/projects/scitex/containers/scitex-user-workspace.sif \\
    python {script_path}
"""

        # Submit to SLURM
        try:
            result = subprocess.run(
                ["sbatch", "-"],
                input=slurm_script.encode(),
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )

            # Parse job ID from SLURM output: "Submitted batch job 12345"
            job_id = result.stdout.strip().split()[-1]

            logger.info(f"Submitted HPC job {job_id} for user {user.username}")
            return job_id

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to submit HPC job: {e.stderr}"
            logger.error(error_msg)
            raise SingularityError(error_msg)

        except subprocess.TimeoutExpired:
            error_msg = "HPC job submission timed out"
            logger.error(error_msg)
            raise SingularityError(error_msg)

    def get_hpc_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get SLURM job status

        Args:
            job_id: SLURM job ID

        Returns:
            Dict with status, runtime, node
        """
        try:
            result = subprocess.run(
                ["squeue", "-j", job_id, "-o", "%T,%M,%R"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )

            # Parse output: "RUNNING,00:15:32,node123"
            parts = result.stdout.strip().split(',')

            if len(parts) >= 3:
                status, runtime, node = parts[:3]
                return {
                    'status': status,
                    'runtime': runtime,
                    'node': node,
                    'found': True,
                }
            else:
                return {
                    'status': 'UNKNOWN',
                    'runtime': '',
                    'node': '',
                    'found': False,
                }

        except subprocess.CalledProcessError:
            # Job not found or completed
            return {
                'status': 'NOT_FOUND',
                'runtime': '',
                'node': '',
                'found': False,
            }

        except subprocess.TimeoutExpired:
            return {
                'status': 'TIMEOUT',
                'runtime': '',
                'node': '',
                'found': False,
            }


# EOF
