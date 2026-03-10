#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SLURM batch script generation."""

from __future__ import annotations

from pathlib import Path
from typing import Dict


def create_batch_script(
    user_id: str,
    script_path: Path,
    container_path: Path,
    workspace: Path,
    job_name: str,
    partition: str,
    cpus: int,
    memory_gb: int,
    time_limit: str,
    env_vars: Dict[str, str],
) -> str:
    """
    Generate SLURM batch script content.

    Creates a bash script with SBATCH directives and Apptainer execution.
    """
    # Ensure output directory exists
    output_dir = workspace / "slurm_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Format environment variables
    env_exports = "\n".join([f"export {k}={v}" for k, v in env_vars.items()])

    return f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --partition={partition}
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem={memory_gb}G
#SBATCH --time={time_limit}
#SBATCH --chdir={workspace}
#SBATCH --output={output_dir}/slurm-%j.out
#SBATCH --error={output_dir}/slurm-%j.err
#SBATCH --account=user_{user_id}

# Environment variables
{env_exports}

# Job information
echo "=========================================="
echo "SLURM Job Information"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: {job_name}"
echo "User: {user_id}"
echo "Node: $(hostname)"
echo "Start Time: $(date)"
echo "CPUs: {cpus}"
echo "Memory: {memory_gb}G"
echo "=========================================="
echo ""

# Execute in Apptainer container
apptainer exec \\
    --contain \\
    --cleanenv \\
    --bind {workspace}:/workspace \\
    --pwd /workspace \\
    {container_path} \\
    python {script_path}

# Capture exit code
EXIT_CODE=$?

echo ""
echo "=========================================="
echo "Job finished: $(date)"
echo "Exit console: $EXIT_CODE"
echo "=========================================="

exit $EXIT_CODE
"""


# EOF
