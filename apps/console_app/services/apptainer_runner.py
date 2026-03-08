#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apptainer sandbox runner — wraps arbitrary commands in an Apptainer container.

Used by services, compilation, and dev apps to ensure user code never runs
directly in the Django process. All user-supplied code runs inside
an Apptainer container with only the project dir visible.
"""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_container_path() -> str:
    """Get the Apptainer container path from Django config."""
    from apps.console_app.views.terminal.config import BASE_CONTAINER_PATH

    return BASE_CONTAINER_PATH


def build_apptainer_exec_cmd(
    inner_cmd: List[str],
    project_dir: Path,
    extra_binds: Optional[List[str]] = None,
    env_vars: Optional[Dict[str, str]] = None,
) -> List[str]:
    """
    Build an ``apptainer exec`` command wrapping ``inner_cmd``.

    Security flags applied:
    - ``--contain``: isolated /tmp and /var/tmp
    - ``--cleanenv``: clean environment (no host env leakage)
    - ``--no-home``: home directory not mounted

    The project directory is bound read-write at ``/workspace``.
    """
    container = _get_container_path()

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
    """
    Run ``inner_cmd`` inside Apptainer with ``project_dir`` bound to ``/workspace``.

    Streams stdout line-by-line to ``log_callback`` if provided.

    Returns:
        Dict with keys: stdout, stderr, returncode, execution_time, success.
    """
    cmd = build_apptainer_exec_cmd(
        inner_cmd=inner_cmd,
        project_dir=project_dir,
        extra_binds=extra_binds,
        env_vars=env_vars,
    )

    logger.info("[apptainer_runner] cmd: %s", " ".join(cmd))

    start = time.time()
    stdout_lines: List[str] = []

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(project_dir),
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
        execution_time = time.time() - start

        return {
            "stdout": "\n".join(stdout_lines),
            "stderr": "",
            "returncode": proc.returncode,
            "execution_time": execution_time,
            "success": proc.returncode == 0,
        }

    except FileNotFoundError:
        msg = "apptainer executable not found — cannot sandbox execution"
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


# EOF
