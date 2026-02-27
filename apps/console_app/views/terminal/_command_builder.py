# Timestamp: "2026-02-25"
# File: apps/console_app/views/terminal/_command_builder.py
"""
Shared Apptainer + SLURM command builder.

Delegates to ``scitex_container.apptainer`` for the actual command
construction, passing Django configuration as explicit parameters.
This module is the single integration point between Django config
and the scitex-container library.
"""

from pathlib import Path

from scitex_container.apptainer import (
    build_dev_pythonpath,
    build_exec_args,
    build_host_mount_binds,
    build_srun_command,
    is_sandbox,
)

from .config import (
    DEV_REPOS,
    HOST_MOUNTS,
    HOST_TEXLIVE_PREFIX,
    SLURM_CPUS,
    SLURM_MEMORY_GB,
    SLURM_PARTITION,
    SLURM_TIME_LIMIT,
)

# Re-export library functions that need no config wrapping
__all__ = [
    "is_sandbox",
    "build_dev_pythonpath",
    "build_host_mount_binds",
    "build_apptainer_args",
    "build_srun_command",
]


def build_apptainer_args(
    container_path: str,
    username: str,
    host_user_dir: Path,
    host_project_dir: Path,
    project_slug: str,
) -> list[str]:
    """Build ``apptainer exec`` args, injecting Django config automatically."""
    return build_exec_args(
        container_path=container_path,
        username=username,
        host_user_dir=host_user_dir,
        host_project_dir=host_project_dir,
        project_slug=project_slug,
        dev_repos=DEV_REPOS or None,
        host_mounts=HOST_MOUNTS or None,
        texlive_prefix=HOST_TEXLIVE_PREFIX,
    )


def build_srun_cmd(
    container_path: str,
    username: str,
    host_user_dir: Path,
    host_project_dir: Path,
    project_slug: str,
    screen_session: str = "scitex-0",
) -> list[str]:
    """Build ``srun`` + ``apptainer`` command, injecting Django config automatically."""
    cmd = build_srun_command(
        container_path=container_path,
        username=username,
        host_user_dir=host_user_dir,
        host_project_dir=host_project_dir,
        project_slug=project_slug,
        dev_repos=DEV_REPOS or None,
        host_mounts=HOST_MOUNTS or None,
        texlive_prefix=HOST_TEXLIVE_PREFIX,
        slurm_partition=SLURM_PARTITION,
        slurm_time_limit=SLURM_TIME_LIMIT,
        slurm_cpus=SLURM_CPUS,
        slurm_memory_gb=SLURM_MEMORY_GB,
        screen_session=screen_session,
    )
    # Use full path for screen and set SCREENDIR to avoid inode overflow on NAS.
    # Screen requires SCREENDIR to have mode 700, so we create a user-specific dir.
    cmd = [
        arg.replace(
            "exec screen ",
            "mkdir -p /tmp/screen-$USER && chmod 700 /tmp/screen-$USER && "
            "export SCREENDIR=/tmp/screen-$USER && exec /usr/bin/screen "
        ).replace(
            "exec /usr/bin/screen ",
            "mkdir -p /tmp/screen-$USER && chmod 700 /tmp/screen-$USER && "
            "export SCREENDIR=/tmp/screen-$USER && exec /usr/bin/screen "
        )
        for arg in cmd
    ]
    return cmd


# EOF
