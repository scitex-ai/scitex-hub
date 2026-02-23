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
    SLURM_CONTAINER_PATH,
    SLURM_CPUS,
    SLURM_MEMORY_GB,
    SLURM_PARTITION,
    SLURM_TIME_LIMIT,
    SLURM_USER_DATA_ROOT,
)

logger = logging.getLogger(__name__)


class SlurmUnavailableError(Exception):
    """Raised when SLURM is not available but required"""

    pass


def check_slurm_status() -> tuple[bool, str]:
    """
    Check SLURM availability via scontrol (fast, doesn't allocate resources).

    Returns:
        Tuple of (available: bool, status: str)
        - (True, "ready") - SLURM controller responding
        - (False, "unavailable") - SLURM not responding
        - (False, "not_installed") - SLURM not installed
    """
    try:
        # Check if scontrol can ping the controller (fast, no resource allocation)
        result = subprocess.run(
            ["scontrol", "ping"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.debug(f"SLURM controller responding (partition: {SLURM_PARTITION})")
            return (True, "ready")
        else:
            logger.error("SLURM controller not responding")
            return (False, "unavailable")

    except subprocess.TimeoutExpired:
        logger.error("SLURM controller timeout")
        return (False, "unavailable")
    except FileNotFoundError:
        logger.error("SLURM not installed")
        return (False, "not_installed")


def is_slurm_available() -> bool:
    """Legacy wrapper for backward compatibility."""
    available, _ = check_slurm_status()
    return available


class ContainerNotFoundError(Exception):
    """Raised when no valid Apptainer SIF container is found"""

    pass


def select_container(user_data_dir: Path, project_dir: Path) -> str:
    """
    Select container with priority:
    1. Project-specific: ~/proj/{project}/.singularity/custom.sif
    2. User default: ~/.singularity/default.sif
    3. Base image: (from SLURM_CONTAINER_PATH config)

    Raises ContainerNotFoundError if no valid SIF exists.
    SECURITY: Never returns a path to a non-existent container.
    """
    # Project-specific container
    project_sif = project_dir / ".singularity" / "custom.sif"
    if project_sif.exists():
        logger.debug(f"Using project container: {project_sif}")
        return str(project_sif)

    # User default container
    user_sif = user_data_dir / ".singularity" / "default.sif"
    if user_sif.exists():
        logger.debug(f"Using user container: {user_sif}")
        return str(user_sif)

    # Base container — validate it exists
    # SLURM_CONTAINER_PATH is the host path (for SLURM jobs on compute nodes).
    # BASE_CONTAINER_PATH is the Docker-internal path (/app/singularity/...).
    # We validate via the Docker path (accessible from here), but return the
    # host path for SLURM execution.
    from .config import BASE_CONTAINER_PATH

    docker_sif = Path(BASE_CONTAINER_PATH)
    host_sif = Path(SLURM_CONTAINER_PATH)

    if not docker_sif.exists() and not host_sif.exists():
        logger.error(
            f"Base container NOT FOUND: checked {BASE_CONTAINER_PATH} (Docker) "
            f"and {SLURM_CONTAINER_PATH} (host) — "
            f"build with: sudo apptainer build "
            f"deployment/singularity/scitex-cloud-shared-v0.1.0.def"
        )
        raise ContainerNotFoundError(
            f"Apptainer SIF not found at {SLURM_CONTAINER_PATH}. "
            f"Terminal cannot start without container isolation."
        )

    logger.debug(f"Using base container: {SLURM_CONTAINER_PATH}")
    return SLURM_CONTAINER_PATH


def exec_slurm_shell(
    username: str,
    user_data_dir: Path,
    project_dir: Path,
    container_path: str,
    project_slug: str,
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

    # Dev mode: editable source mounts
    from .config import FIGRECIPE_DEV_SRC, SCITEX_DEV_SRC

    dev_bind_args = []
    # Note: we skip is_dir() because these are HOST paths (for SLURM),
    # not visible from inside the Django Docker container.
    if SCITEX_DEV_SRC:
        dev_bind_args += [
            "--bind",
            f"{SCITEX_DEV_SRC}:/usr/local/lib/python3.11/site-packages/scitex:rw",
        ]
        logger.debug(f"Dev mode: mounting editable scitex from {SCITEX_DEV_SRC}")
    if FIGRECIPE_DEV_SRC:
        dev_bind_args += [
            "--bind",
            f"{FIGRECIPE_DEV_SRC}:/usr/local/lib/python3.11/site-packages/figrecipe:rw",
        ]
        logger.debug(f"Dev mode: mounting editable figrecipe from {FIGRECIPE_DEV_SRC}")

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
        container_cmd,
        "shell",
        "--containall",
        "--cleanenv",
        "--writable-tmpfs",
        "--hostname",
        "scitex-cloud",
        # Pass env vars through --cleanenv (Apptainer strips inherited vars)
        "--env",
        "TERM=xterm-256color",
        "--env",
        "SCITEX_CLOUD=true",
        "--env",
        f"SCITEX_PROJECT={project_slug}",
        "--env",
        f"SCITEX_USER={username}",
        "--env",
        f"USER={username}",
        "--env",
        f"LOGNAME={username}",
        "--home",
        f"{host_user_dir}:/home/{username}",
        "--bind",
        f"{host_project_dir}:/home/{username}/proj/{project_slug}:rw",
        *dev_bind_args,
        "--pwd",
        f"/home/{username}/proj/{project_slug}",
        container_path,  # Use host path to SIF
    ]

    # Environment for srun process (host-side, before exec into container)
    env = {
        "TERM": "xterm-256color",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }

    logger.debug(
        f"Spawning SLURM terminal: user={username} partition={SLURM_PARTITION}"
    )
    logger.debug(f"SLURM command: {' '.join(cmd)}")

    # Note: host_user_dir and host_project_dir are HOST paths (not visible from container)
    # SLURM will run on the host where these paths exist

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
