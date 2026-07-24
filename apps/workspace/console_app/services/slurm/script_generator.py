#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SLURM batch script generation."""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Dict

# Tenant-controlled fields are interpolated into a bash script that SLURM
# executes, so any shell metacharacter is a command-injection vector (CWE-78).
# Fields that land in #SBATCH directives (job_name/partition/time_limit) or in
# arithmetic contexts (cpus/memory_gb) CANNOT be shell-quoted — SLURM parses
# them, so a quote would be literal — therefore they are validated and rejected.
# Fields that land in bash (env values, paths) are shlex.quote()d instead.
_JOB_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_PARTITION_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_TIME_LIMIT_RE = re.compile(r"^[0-9][0-9:.\-]{0,19}$")
_ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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

    Raises:
        ValueError: if any tenant-controlled field contains shell/SLURM
            metacharacters (rejected rather than silently sanitized).
    """
    # ---- Validate/sanitize tenant-controlled inputs (CWE-78 defense) ----
    if not isinstance(job_name, str) or not _JOB_NAME_RE.match(job_name):
        raise ValueError(
            "Invalid job_name: only letters, digits, '.', '_', '-' "
            "(1-64 chars) are allowed"
        )
    if not isinstance(partition, str) or not _PARTITION_RE.match(partition):
        raise ValueError("Invalid partition name")
    if not isinstance(time_limit, str) or not _TIME_LIMIT_RE.match(time_limit):
        raise ValueError("Invalid time_limit (expected e.g. 01:00:00)")
    try:
        cpus = int(cpus)
        memory_gb = int(memory_gb)
    except (TypeError, ValueError):
        raise ValueError("cpus and memory_gb must be integers")
    if cpus < 1 or memory_gb < 1:
        raise ValueError("cpus and memory_gb must be >= 1")

    # Environment variable NAMES must be valid shell identifiers; VALUES are
    # shell-quoted so no metacharacter can break out of the `export`.
    env_lines = []
    for k, v in (env_vars or {}).items():
        if not isinstance(k, str) or not _ENV_KEY_RE.match(k):
            raise ValueError(f"Invalid environment variable name: {k!r}")
        env_lines.append(f"export {k}={shlex.quote(str(v))}")
    env_exports = "\n".join(env_lines)

    # Ensure output directory exists
    output_dir = workspace / "slurm_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Paths are server-derived, but shell-quote them defensively where they
    # land in bash (the apptainer/python command line, not #SBATCH directives).
    q_workspace = shlex.quote(str(workspace))
    q_container = shlex.quote(str(container_path))
    q_script = shlex.quote(str(script_path))

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
    --bind {q_workspace}:/workspace \\
    --pwd /workspace \\
    {q_container} \\
    python {q_script}

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
