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
    SLURM_PARTITION,
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
    # Project-specific container (SIF file or sandbox directory)
    project_sif = project_dir / ".singularity" / "custom.sif"
    if project_sif.is_file() or project_sif.is_dir():
        logger.debug(f"Using project container: {project_sif}")
        return str(project_sif)

    # User default container (SIF file or sandbox directory)
    user_sif = user_data_dir / ".singularity" / "default.sif"
    if user_sif.is_file() or user_sif.is_dir():
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

    docker_exists = docker_sif.is_file() or docker_sif.is_dir()
    host_exists = host_sif.is_file() or host_sif.is_dir()
    if not docker_exists and not host_exists:
        logger.error(
            f"Base container NOT FOUND: checked {BASE_CONTAINER_PATH} (Docker) "
            f"and {SLURM_CONTAINER_PATH} (host) — "
            f"build SIF with: sudo apptainer build deployment/singularity/scitex-final.def "
            f"or sandbox with: sudo apptainer build --sandbox deployment/singularity/scitex-final.def"
        )
        raise ContainerNotFoundError(
            f"Apptainer container (SIF or sandbox) not found at {SLURM_CONTAINER_PATH}. "
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
    screen_session: str = "scitex-0",
):
    """
    Execute shell via SLURM (REQUIRED for all users).

    SECURITY: This is the ONLY way to spawn terminals. No fallbacks allowed.
    """
    # Convert Docker paths to host paths for SLURM
    # SLURM jobs run on compute nodes, not inside Docker
    host_user_dir = SLURM_USER_DATA_ROOT / username
    host_project_dir = host_user_dir / "proj" / project_slug

    from ._command_builder import build_srun_cmd

    cmd = build_srun_cmd(
        container_path=container_path,
        username=username,
        host_user_dir=host_user_dir,
        host_project_dir=host_project_dir,
        project_slug=project_slug,
        screen_session=screen_session,
    )

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

    # host_user_dir and host_project_dir are HOST paths.
    # os.chdir() cannot access these from inside Docker — use srun --chdir instead.
    # srun inherits --chdir and passes it to the SLURM job on the host.
    srun_chdir = str(host_project_dir)
    logger.info(f"[Terminal] Setting srun --chdir={srun_chdir} for {username}")

    # Insert --chdir before the srun command target (after 'srun' and its flags)
    try:
        chdir_idx = 1  # After 'srun'
        cmd.insert(chdir_idx, f"--chdir={srun_chdir}")
    except Exception as e:
        logger.error(f"[Terminal] Failed to insert --chdir into srun cmd: {e}")

    # Set cwd to /tmp as safe default for the Docker-side exec
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
