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
    APPTAINER_OVERLAY_ENABLED,
    DEV_REPOS,
    HOST_MOUNTS,
    HOST_TEXLIVE_PREFIX,
    OVERLAY_ROOT,
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
    "resolve_overlay_kwargs",
    "build_apptainer_args",
    "build_srun_command",
    "build_instance_start_script_cmd",
    "build_sbatch_cmd",
    "build_shell_in_allocation_cmd",
]


def resolve_overlay_kwargs(
    username: str,
    *,
    enabled: bool,
    overlay_root: str,
) -> dict:
    """Resolve the persistent-overlay kwargs for the scitex_container builders.

    Pure decision helper for the SIF+overlay migration (DEFAULT OFF).

    Parameters
    ----------
    username : str
        Session username; selects the per-user overlay image.
    enabled : bool
        Whether persistent overlays are enabled (the
        ``APPTAINER_OVERLAY_ENABLED`` flag).
    overlay_root : str
        Host directory holding per-user overlay images
        (the ``OVERLAY_ROOT`` config value).

    Returns
    -------
    dict
        When ``enabled`` is True: ``{"overlay_path": "<root>/<user>.img",
        "fakeroot": True}``. When False: an EMPTY dict, so splatting it
        into a builder call (``build_exec_args(..., **kwargs)``) passes
        nothing extra and the emitted command is byte-identical to the
        ephemeral ``--writable-tmpfs`` behavior.
    """
    if not enabled:
        return {}
    return {
        "overlay_path": f"{overlay_root}/{username}.img",
        "fakeroot": True,
    }


def build_apptainer_args(
    container_path: str,
    username: str,
    host_user_dir: Path,
    host_project_dir: Path,
    project_slug: str,
) -> list[str]:
    """Build ``apptainer exec`` args, injecting Django config automatically."""
    overlay_kwargs = resolve_overlay_kwargs(
        username,
        enabled=APPTAINER_OVERLAY_ENABLED,
        overlay_root=OVERLAY_ROOT,
    )
    return build_exec_args(
        container_path=container_path,
        username=username,
        host_user_dir=host_user_dir,
        host_project_dir=host_project_dir,
        project_slug=project_slug,
        dev_repos=DEV_REPOS or None,
        host_mounts=HOST_MOUNTS or None,
        texlive_prefix=HOST_TEXLIVE_PREFIX,
        **overlay_kwargs,
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
    overlay_kwargs = resolve_overlay_kwargs(
        username,
        enabled=APPTAINER_OVERLAY_ENABLED,
        overlay_root=OVERLAY_ROOT,
    )
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
        **overlay_kwargs,
    )


def build_instance_start_script_cmd(
    container_path: str,
    username: str,
    host_user_dir: Path,
    host_project_dir: Path,
    project_slug: str,
    instance_name: str,
) -> str:
    """Build instance start script, injecting Django config automatically.

    Prepends a stale-instance cleanup step so that leftover instances
    from cancelled jobs or restarts don't block new allocations.
    """
    import shlex

    overlay_kwargs = resolve_overlay_kwargs(
        username,
        enabled=APPTAINER_OVERLAY_ENABLED,
        overlay_root=OVERLAY_ROOT,
    )
    script = build_instance_start_script(
        container_path=container_path,
        username=username,
        host_user_dir=host_user_dir,
        host_project_dir=host_project_dir,
        project_slug=project_slug,
        instance_name=instance_name,
        dev_repos=DEV_REPOS or None,
        host_mounts=HOST_MOUNTS or None,
        texlive_prefix=HOST_TEXLIVE_PREFIX,
        **overlay_kwargs,
    )

    # Inject stale-instance cleanup before "apptainer instance start"
    instance_quoted = shlex.quote(instance_name)
    cleanup = (
        f"# Stop stale instance if it exists from a previous allocation\n"
        f"if apptainer instance list 2>/dev/null | grep -q {instance_quoted}; then\n"
        f"    apptainer instance stop {instance_quoted} 2>/dev/null || true\n"
        f"    sleep 1\n"
        f"fi\n"
    )
    script = script.replace(
        "apptainer instance start",
        cleanup + "apptainer instance start",
        1,
    )
    return script


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
    import inspect

    sig = inspect.signature(build_shell_in_allocation_command)
    kwargs = dict(job_id=job_id, instance_name=instance_name, username=username)
    if "project_slug" in sig.parameters:
        kwargs["project_slug"] = project_slug
    return build_shell_in_allocation_command(**kwargs)


# EOF
