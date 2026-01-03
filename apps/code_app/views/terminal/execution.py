"""
Shell Execution via SLURM Only
SECURITY CRITICAL: All interactive terminals MUST go through SLURM for resource control.

No fallback to direct Apptainer - this is a security requirement for multi-user systems.

Note on SLURM PTY errors:
    The error "srun: error: pty: accept failure: Interrupted system call" is
    a known SLURM issue (SchedMD Bug #3979). It occurs when signals interrupt
    the accept() call during PTY setup. This is typically harmless - the terminal
    still works. Signal handling in consumer.py mitigates this issue.
"""

import logging
import os
import signal
import subprocess
from pathlib import Path

from .config import (
    SLURM_PARTITION,
    SLURM_TIME_LIMIT,
    SLURM_CPUS,
    SLURM_MEMORY_GB,
    SLURM_CONTAINER_PATH,
    SLURM_USER_DATA_ROOT,
)

logger = logging.getLogger(__name__)


class SlurmUnavailableError(Exception):
    """Raised when SLURM is not available but required"""
    pass


def is_slurm_available() -> bool:
    """
    Check if SLURM controller is available and responsive.

    SECURITY: This system requires SLURM for all terminal sessions.
    If SLURM is not available, terminals will be disabled.
    """
    try:
        # First check if srun exists
        result = subprocess.run(
            ["srun", "--version"],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            logger.error("SLURM binary not found - terminals DISABLED for security")
            return False

        # Verify controller connectivity with actual partition and resources
        # Note: Don't use --pty here as Django doesn't have a TTY
        test_result = subprocess.run(
            ["timeout", "2", "srun",
             f"--partition={SLURM_PARTITION}",
             f"--cpus-per-task=1",
             f"--mem=1G",
             "true"],
            capture_output=True,
            timeout=5
        )

        if test_result.returncode == 0:
            # Check if the job actually ran or if it was just queued
            stderr = test_result.stderr.decode('utf-8', errors='replace')
            if 'queued and waiting for resources' in stderr or 'Requested partition configuration not available' in stderr:
                logger.error(f"SLURM partition '{SLURM_PARTITION}' unavailable - check SLURM configuration")
                return False
            logger.info(f"SLURM operational - terminals enabled (partition: {SLURM_PARTITION})")
            return True
        elif test_result.returncode == 124:
            logger.error("SLURM controller timeout - terminals DISABLED")
            return False
        else:
            logger.error(f"SLURM controller not responding (exit {test_result.returncode}) - terminals DISABLED")
            return False

    except subprocess.TimeoutExpired:
        logger.error("SLURM controller connection timeout - terminals DISABLED")
        return False
    except FileNotFoundError:
        logger.error("SLURM not installed - terminals DISABLED for security")
        return False


def select_container(user_data_dir: Path, project_dir: Path) -> str:
    """
    Select container with priority:
    1. Project-specific: ~/proj/{project}/.singularity/custom.sif
    2. User default: ~/.singularity/default.sif
    3. Base image: (from SLURM_CONTAINER_PATH config)
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
    logger.info(f"Using base container: {SLURM_CONTAINER_PATH}")
    return SLURM_CONTAINER_PATH


def exec_slurm_shell(
    username: str,
    user_data_dir: Path,
    project_dir: Path,
    container_path: str,
    project_slug: str
):
    """
    Execute shell via SLURM (REQUIRED for all users).

    SECURITY: This is the ONLY way to spawn terminals. No fallbacks allowed.
    """
    # Container command on SLURM compute nodes
    container_cmd = "apptainer"

    # Convert Docker paths to host paths for SLURM
    # SLURM jobs run on compute nodes, not inside Docker
    host_user_dir = SLURM_USER_DATA_ROOT / username
    host_project_dir = host_user_dir / "proj" / project_slug

    # Build srun command with host paths
    cmd = [
        "srun",
        "--pty",
        "--chdir=/tmp",  # Explicit host cwd (prevents /app warning)
        f"--partition={SLURM_PARTITION}",
        f"--time={SLURM_TIME_LIMIT}",
        f"--cpus-per-task={SLURM_CPUS}",
        f"--mem={SLURM_MEMORY_GB}G",
        f"--job-name=terminal_{username}",
        # Note: --account not used (SLURM accounting not configured)
        # Container execution (using host paths)
        container_cmd, "shell",
        "--containall",
        "--cleanenv",
        "--writable-tmpfs",
        "--hostname", "scitex-cloud",
        "--home", f"{host_user_dir}:/home/{username}",
        "--bind", f"{host_project_dir}:/home/{username}/proj/{project_slug}:rw",
        "--pwd", f"/home/{username}/proj/{project_slug}",
        container_path,  # Use host path to SIF
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

    logger.info(f"Spawning SLURM terminal: user={username} partition={SLURM_PARTITION} time={SLURM_TIME_LIMIT}")

    # Change to a directory that exists on the host (srun inherits cwd)
    # The Django container runs from /app which doesn't exist on the host
    os.chdir("/tmp")

    # Reset signal handlers to default before exec to avoid EINTR in srun
    # This helps prevent "pty: accept failure: Interrupted system call" errors
    for sig in (signal.SIGCHLD, signal.SIGWINCH, signal.SIGPIPE):
        try:
            signal.signal(sig, signal.SIG_DFL)
        except (OSError, ValueError):
            pass

    # exec replaces this process with srun
    os.execvpe("srun", cmd, env)
    # Never returns on success


# EOF
