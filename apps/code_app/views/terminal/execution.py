"""
Shell Execution Strategies
Handles different execution modes: SLURM, direct Apptainer, and fallback bash

Note on SLURM PTY errors:
    The error "srun: error: pty: accept failure: Interrupted system call" is
    a known SLURM issue (SchedMD Bug #3979). It occurs when signals interrupt
    the accept() call during PTY setup. This is typically harmless - the terminal
    still works. Signal handling in consumer.py mitigates this issue.
"""

import logging
import os
import signal
import shutil
import subprocess
from pathlib import Path

from .config import (
    BASE_CONTAINER_PATH,
    SLURM_PARTITION,
    SLURM_TIME_LIMIT,
    SLURM_CPUS,
    SLURM_MEMORY_GB,
    SLURM_CONTAINER_PATH,
    SLURM_USER_DATA_ROOT,
)

logger = logging.getLogger(__name__)


def is_slurm_available() -> bool:
    """Check if SLURM is available on this system"""
    try:
        result = subprocess.run(
            ["srun", "--version"],
            capture_output=True,
            timeout=5
        )
        available = result.returncode == 0
        if available:
            logger.info("SLURM available - using srun for terminal")
        return available
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.info("SLURM not available - using direct Apptainer")
        return False


def select_container(user_data_dir: Path, project_dir: Path) -> str:
    """
    Select container with priority:
    1. Project-specific: ~/proj/{project}/.singularity/custom.sif
    2. User default: ~/.singularity/default.sif
    3. Base image: /app/singularity/scitex-user-workspace.sif
    """
    # Project-specific container
    project_sif = project_dir / ".singularity" / "custom.sif"
    if project_sif.exists():
        logger.info(f"Using project container: {project_sif}")
        return str(project_sif)

    # User default container
    user_sif = user_data_dir / ".singularity" / "default.sif"
    if user_sif.exists():
        logger.info(f"Using user container: {user_sif}")
        return str(user_sif)

    # Base container
    logger.info(f"Using base container: {BASE_CONTAINER_PATH}")
    return BASE_CONTAINER_PATH


def exec_slurm_shell(
    username: str,
    user_data_dir: Path,
    project_dir: Path,
    container_path: str,
    project_slug: str
):
    """Execute shell via SLURM (production mode)"""
    # Detect apptainer or singularity on host (SLURM runs on compute nodes)
    # Most HPC systems have apptainer/singularity in standard paths
    container_cmd = "apptainer"  # Assume host has apptainer

    # Convert Docker paths to host paths for SLURM
    # SLURM jobs run on compute nodes, not inside Docker
    host_user_dir = SLURM_USER_DATA_ROOT / username
    host_project_dir = host_user_dir / "proj" / project_slug

    # Build srun command with host paths
    cmd = [
        "srun",
        "--pty",
        f"--partition={SLURM_PARTITION}",
        f"--time={SLURM_TIME_LIMIT}",
        f"--cpus-per-task={SLURM_CPUS}",
        f"--mem={SLURM_MEMORY_GB}G",
        f"--job-name=terminal_{username}",
        f"--account=user_{username}",
        # Container execution (using host paths)
        container_cmd, "shell",
        "--containall",
        "--cleanenv",
        "--writable-tmpfs",
        "--hostname", "scitex-cloud",
        "--home", f"{host_user_dir}:/home/{username}",
        "--bind", f"{host_project_dir}:/home/{username}/proj/{project_slug}:rw",
        "--pwd", f"/home/{username}/proj/{project_slug}",
        SLURM_CONTAINER_PATH,  # Use host path to SIF
    ]

    # Environment
    env = {
        "TERM": "xterm-256color",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "SCITEX_CLOUD": "true",
        "SCITEX_PROJECT": project_slug,
        "SCITEX_USER": username,
    }

    logger.info(f"Spawning SLURM terminal for {username}: srun → {container_cmd}")

    # Reset signal handlers to default before exec to avoid EINTR in srun
    # This helps prevent "pty: accept failure: Interrupted system call" errors
    for sig in (signal.SIGCHLD, signal.SIGWINCH, signal.SIGPIPE):
        try:
            signal.signal(sig, signal.SIG_DFL)
        except (OSError, ValueError):
            pass

    os.execvpe("srun", cmd, env)


def exec_direct_shell(
    username: str,
    user_data_dir: Path,
    project_dir: Path,
    container_path: str,
    project_slug: str
):
    """Execute shell directly via Apptainer (dev fallback)"""
    container_cmd = "apptainer" if shutil.which("apptainer") else "singularity"

    if not shutil.which(container_cmd):
        # Ultimate fallback: plain bash (only for development)
        logger.warning("No container runtime - using plain bash (DEV ONLY)")
        exec_plain_bash(username, project_dir, project_slug)
        return

    # Check if container image exists and is accessible
    if not Path(container_path).exists():
        logger.warning(f"Container image not found: {container_path} - using plain bash")
        exec_plain_bash(username, project_dir, project_slug)
        return

    # Build container command
    # Note: --fakeroot requires /etc/subuid mappings, which don't exist in Docker
    # For Docker environments, run without fakeroot (Docker already provides isolation)
    cmd = [
        container_cmd, "shell",
        "--writable-tmpfs",
        "--hostname", "scitex-cloud",
        "--home", f"{user_data_dir}:/home/{username}",
        "--bind", f"{project_dir}:/home/{username}/proj/{project_slug}:rw",
        "--pwd", f"/home/{username}/proj/{project_slug}",
        container_path,
    ]

    env = {
        "TERM": "xterm-256color",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "SCITEX_CLOUD": "true",
        "SCITEX_PROJECT": project_slug,
        "SCITEX_USER": username,
    }

    logger.info(f"Spawning direct terminal for {username}: {container_cmd} shell")
    os.execvpe(container_cmd, cmd, env)


def exec_plain_bash(username: str, project_dir: Path, project_slug: str):
    """Fallback to plain bash when container execution fails"""
    logger.warning(f"Falling back to plain bash for {username}")
    os.chdir(str(project_dir))
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["SCITEX_CLOUD"] = "true"
    env["SCITEX_PROJECT"] = project_slug
    os.execvpe("/bin/bash", ["bash", "--login"], env)


# EOF
