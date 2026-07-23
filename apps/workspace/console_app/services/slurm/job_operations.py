#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SLURM job submission and status operations."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional

from .script_generator import create_batch_script

logger = logging.getLogger(__name__)


def submit_job(
    job_scripts_dir: Path,
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
    """
    Submit a job to SLURM.

    Args:
        job_scripts_dir: Directory to store batch scripts
        user_id: User identifier for accounting
        script_path: Path to Python script inside container
        container_path: Path to Apptainer .sif file
        workspace: User workspace directory (will be bound to /workspace)
        job_name: Name for the SLURM job
        partition: SLURM partition (normal/express/long)
        cpus: Number of CPUs to allocate
        memory_gb: Memory in GB
        time_limit: Time limit in HH:MM:SS format
        env_vars: Environment variables to export

    Returns:
        Dict with success, job_id, partition, and message keys
    """
    # Create batch script. create_batch_script rejects tenant-controlled
    # fields containing shell/SLURM metacharacters (CWE-78) — fail closed
    # (do NOT submit) with the validation message rather than raising.
    try:
        batch_script = create_batch_script(
            user_id=user_id,
            script_path=script_path,
            container_path=container_path,
            workspace=workspace,
            job_name=job_name,
            partition=partition,
            cpus=cpus,
            memory_gb=memory_gb,
            time_limit=time_limit,
            env_vars=env_vars or {},
        )
    except ValueError as e:
        logger.warning(f"Rejected job submission for user {user_id}: {e}")
        return {"success": False, "message": str(e)}

    # Save batch file
    batch_file = job_scripts_dir / f"job_{user_id}_{job_name}.sh"
    batch_file.write_text(batch_script)
    batch_file.chmod(0o755)

    logger.info(f"Created batch script: {batch_file}")

    # Submit to SLURM
    cmd = ["sbatch", str(batch_file)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Parse output: "Submitted batch job 12345"
        job_id = int(result.stdout.strip().split()[-1])
        logger.info(f"Job {job_id} submitted for user {user_id}")
        return {
            "success": True,
            "job_id": job_id,
            "partition": partition,
            "message": f"Job {job_id} submitted successfully",
        }
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip()
        logger.error(f"Job submission failed for user {user_id}: {error_msg}")
        return {"success": False, "message": error_msg}


def get_job_status(job_id: int) -> Dict:
    """
    Get status of a SLURM job.

    Args:
        job_id: SLURM job ID

    Returns:
        Dict with job status information
    """
    # Check active queue first (running/pending jobs)
    cmd = ["squeue", "-j", str(job_id), "-o", "%T %M %r", "--noheader"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout.strip():
        parts = result.stdout.strip().split()
        state = parts[0]
        time_used = parts[1] if len(parts) > 1 else "0:00"
        reason = parts[2] if len(parts) > 2 else "None"

        return {
            "job_id": job_id,
            "state": state,
            "time_used": time_used,
            "reason": reason,
            "is_running": state == "RUNNING",
            "is_pending": state == "PENDING",
            "is_completed": False,
        }

    # Check completed jobs (sacct)
    cmd = [
        "sacct",
        "-j",
        str(job_id),
        "-o",
        "State,ExitCode,Elapsed",
        "--noheader",
        "--parsable2",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout.strip():
        line = result.stdout.strip().split("\n")[0]
        parts = line.split("|")
        state = parts[0] if len(parts) > 0 else "UNKNOWN"
        exit_code = parts[1] if len(parts) > 1 else "1:0"
        elapsed = parts[2] if len(parts) > 2 else "0:00"

        return {
            "job_id": job_id,
            "state": state,
            "exit_code": exit_code,
            "elapsed": elapsed,
            "is_completed": True,
            "is_running": False,
            "is_pending": False,
            "success": state == "COMPLETED" and exit_code == "0:0",
        }

    # Job not found
    return {
        "job_id": job_id,
        "state": "NOT_FOUND",
        "is_completed": False,
        "is_running": False,
        "is_pending": False,
    }


def cancel_job(job_id: int) -> Dict:
    """
    Cancel a SLURM job.

    Args:
        job_id: SLURM job ID to cancel

    Returns:
        Dict with success and message keys
    """
    cmd = ["scancel", str(job_id)]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Job {job_id} cancelled")
        return {"success": True, "message": f"Job {job_id} cancelled"}
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip()
        logger.error(f"Failed to cancel job {job_id}: {error_msg}")
        return {"success": False, "message": error_msg}


def get_job_output(job_id: int, workspace: Path, tail_lines: int = 100) -> Dict:
    """
    Get job output logs.

    Args:
        job_id: SLURM job ID
        workspace: User workspace directory
        tail_lines: Number of lines to return from end of file

    Returns:
        Dict with stdout, stderr, and found keys
    """
    output_dir = workspace / "slurm_outputs"
    stdout_file = output_dir / f"slurm-{job_id}.out"
    stderr_file = output_dir / f"slurm-{job_id}.err"

    result = {"found": False, "stdout": "", "stderr": ""}

    if stdout_file.exists():
        result["found"] = True
        lines = stdout_file.read_text().split("\n")
        result["stdout"] = (
            "\n".join(lines[-tail_lines:]) if tail_lines else "\n".join(lines)
        )

    if stderr_file.exists():
        result["found"] = True
        lines = stderr_file.read_text().split("\n")
        result["stderr"] = (
            "\n".join(lines[-tail_lines:]) if tail_lines else "\n".join(lines)
        )

    return result


# EOF
