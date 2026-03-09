#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apptainer sandbox runner.

Primary path: reuse the user's existing SLURM allocation via ``srun --overlap``.
This is simpler, safer, and faster — no new container startup, proper resource
accounting, and runs inside the user's already-active Apptainer instance.

Fallback path: local ``apptainer exec`` when no allocation is active.
"""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_container_path() -> str:
    from apps.console_app.views.terminal.config import BASE_CONTAINER_PATH

    return BASE_CONTAINER_PATH


def get_container_for_user(username: str) -> str:
    """Return the Apptainer container path for a user.

    Resolution order (first non-empty wins):
    1. User's ``UserProfile.apptainer_container_path``
    2. Shared default from ``BASE_CONTAINER_PATH``
    """
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.select_related("profile").get(username=username)
        path = getattr(user.profile, "apptainer_container_path", "")
        if path:
            return path
    except Exception:
        pass
    return _get_container_path()


def _instance_name(username: str) -> str:
    return f"scitex-{username}"


def _run_streaming_cmd(
    cmd: List[str],
    cwd: Path,
    timeout: int,
    log_callback: Optional[Callable[[str], None]],
) -> Dict[str, Any]:
    """Run cmd, stream stdout line-by-line, enforce timeout. Internal helper."""
    logger.info("[apptainer_runner] %s", " ".join(cmd))
    start = time.time()
    stdout_lines: List[str] = []

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(cwd),
        )

        for raw_line in proc.stdout:
            line = raw_line.rstrip()
            stdout_lines.append(line)
            if log_callback:
                log_callback(line)
            if time.time() - start > timeout:
                proc.kill()
                proc.wait()
                msg = f"Timed out after {timeout}s"
                if log_callback:
                    log_callback(f"[ERROR] {msg}")
                return {
                    "stdout": "\n".join(stdout_lines),
                    "stderr": msg,
                    "returncode": -1,
                    "execution_time": time.time() - start,
                    "success": False,
                }

        proc.wait()
        return {
            "stdout": "\n".join(stdout_lines),
            "stderr": "",
            "returncode": proc.returncode,
            "execution_time": time.time() - start,
            "success": proc.returncode == 0,
        }

    except FileNotFoundError as exc:
        msg = f"Command not found: {exc}"
        logger.error("[apptainer_runner] %s", msg)
        if log_callback:
            log_callback(f"[ERROR] {msg}")
        return {
            "stdout": "",
            "stderr": msg,
            "returncode": -1,
            "execution_time": time.time() - start,
            "success": False,
        }
    except Exception as exc:
        msg = str(exc)
        logger.error("[apptainer_runner] error: %s", msg, exc_info=True)
        return {
            "stdout": "",
            "stderr": msg,
            "returncode": -1,
            "execution_time": time.time() - start,
            "success": False,
        }


def run_in_user_allocation(
    username: str,
    inner_cmd: List[str],
    project_dir: Path,
    timeout: int = 300,
    log_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Run ``inner_cmd`` in the user's SLURM allocation (preferred path).

    If the user has an active terminal session (sbatch job), attaches to it
    via ``srun --overlap`` — no new container startup, proper resource limits.

    Falls back to local ``apptainer exec`` if no allocation is active.

    Args:
        username: Django username (used to find SLURM job and instance).
        inner_cmd: Command to run inside the container.
        project_dir: Host path of the project directory (for fallback bind).
        timeout: Hard timeout in seconds.
        log_callback: Called with each output line as it arrives.
    """
    from apps.console_app.services.terminal_broker.allocation import Allocation

    job_ids = Allocation.find_existing_jobs(username)

    if job_ids:
        job_id = job_ids[0]
        instance = _instance_name(username)
        logger.info(
            "[apptainer_runner] reusing allocation job=%s instance=%s for %s",
            job_id,
            instance,
            username,
        )
        cmd = [
            "srun",
            "--overlap",
            f"--jobid={job_id}",
            "apptainer",
            "instance",
            "exec",
            instance,
            *inner_cmd,
        ]
    else:
        logger.info(
            "[apptainer_runner] no active allocation for %s — using local apptainer exec",
            username,
        )
        cmd = build_apptainer_exec_cmd(
            inner_cmd,
            project_dir,
            container_path=get_container_for_user(username),
        )

    return _run_streaming_cmd(cmd, project_dir, timeout, log_callback)


def build_apptainer_exec_cmd(
    inner_cmd: List[str],
    project_dir: Path,
    extra_binds: Optional[List[str]] = None,
    env_vars: Optional[Dict[str, str]] = None,
    container_path: Optional[str] = None,
) -> List[str]:
    """Build a local ``apptainer exec`` command (fallback when no SLURM allocation).

    Args:
        container_path: Override the container to use. Defaults to shared container.
    """
    container = container_path or _get_container_path()
    cmd = [
        "apptainer",
        "exec",
        "--contain",
        "--cleanenv",
        "--no-home",
        "--bind",
        f"{project_dir}:/workspace:rw",
    ]
    for bind in extra_binds or []:
        cmd.extend(["--bind", bind])
    for key, val in (env_vars or {}).items():
        cmd.extend(["--env", f"{key}={val}"])
    cmd.append(container)
    cmd.extend(inner_cmd)
    return cmd


def run_in_apptainer(
    inner_cmd: List[str],
    project_dir: Path,
    timeout: int = 300,
    log_callback: Optional[Callable[[str], None]] = None,
    extra_binds: Optional[List[str]] = None,
    env_vars: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Local apptainer exec (used by dev_app_runner when no username available)."""
    cmd = build_apptainer_exec_cmd(inner_cmd, project_dir, extra_binds, env_vars)
    return _run_streaming_cmd(cmd, project_dir, timeout, log_callback)


# EOF
