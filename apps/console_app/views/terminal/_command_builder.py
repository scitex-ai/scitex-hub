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
    build_instance_start_script,
    build_sbatch_command,
    build_shell_in_allocation_command,
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
    "build_instance_start_script_cmd",
    "build_sbatch_cmd",
    "build_shell_in_allocation_cmd",
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
    return build_srun_command(
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


def build_instance_start_script_cmd(
    container_path: str,
    username: str,
    host_user_dir: Path,
    host_project_dir: Path,
    project_slug: str,
    instance_name: str,
) -> str:
    """Build instance start script, injecting Django config automatically."""
    return build_instance_start_script(
        container_path=container_path,
        username=username,
        host_user_dir=host_user_dir,
        host_project_dir=host_project_dir,
        project_slug=project_slug,
        instance_name=instance_name,
        dev_repos=DEV_REPOS or None,
        host_mounts=HOST_MOUNTS or None,
        texlive_prefix=HOST_TEXLIVE_PREFIX,
    )


def build_sbatch_cmd(
    instance_name: str,
    script_path: str,
    username: str = "",
    project_slug: str = "",
) -> list[str]:
    """Build ``sbatch`` command, injecting Django SLURM config automatically."""
    return build_sbatch_command(
        instance_name=instance_name,
        script_path=script_path,
        slurm_partition=SLURM_PARTITION,
        slurm_time_limit=SLURM_TIME_LIMIT,
        slurm_cpus=SLURM_CPUS,
        slurm_memory_gb=SLURM_MEMORY_GB,
        username=username,
        project_slug=project_slug,
    )


def build_shell_in_allocation_cmd(
    job_id: str,
    instance_name: str,
    username: str = "",
    project_slug: str = "",
) -> list[str]:
    """Build ``srun --overlap`` command to attach shell inside existing allocation."""
    return build_shell_in_allocation_command(
        job_id=job_id,
        instance_name=instance_name,
        username=username,
        project_slug=project_slug,
    )


# EOF
