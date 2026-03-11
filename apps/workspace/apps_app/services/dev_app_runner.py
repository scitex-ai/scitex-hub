#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DevAppRunner — executes dev app context builders inside Apptainer.

Prevents dev app backend code from running inside the Django process.
Uses JSON stdin/stdout protocol with run_dev_context.py as the sandboxed runner.

Primary path: reuse the user's existing SLURM allocation via run_in_user_allocation.
The runner script is written temporarily to project_dir so it is visible inside
the container at /workspace/.scitex_run_dev_context.py.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Path to the runner script (inside Django container, copied to project dir at runtime)
_RUNNER_SCRIPT = Path(__file__).parent.parent / "scripts" / "run_dev_context.py"


def run_dev_context(
    dev_install,
    username: str,
    project_id: Optional[int],
    project_slug: str,
    get_params: Optional[Dict[str, str]] = None,
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    Run a dev app's context builder inside Apptainer.

    The runner script is written to project_dir/.scitex_run_dev_context.py so
    it is accessible inside the container at /workspace/.scitex_run_dev_context.py.
    JSON input is passed via stdin; output is read from stdout.

    Args:
        dev_install: DevInstallation model instance.
        username: Authenticated user's username.
        project_id: Current project ID (can be None).
        project_slug: Current project slug.
        get_params: GET query parameters dict.
        timeout: Max seconds to wait for context builder.

    Returns:
        Dict to use as template context (empty on error).
    """
    from apps.workspace.apps_app.services.dev_app_loader import resolve_dev_project_dir
    from apps.workspace.console_app.services.apptainer_runner import (
        _instance_name,
        build_apptainer_exec_cmd,
        get_container_for_user,
    )
    from apps.workspace.console_app.services.terminal_broker.allocation import (
        Allocation,
    )

    project_dir = resolve_dev_project_dir(
        dev_install.source_owner, dev_install.source_repo
    )
    if not project_dir:
        logger.warning(
            "[DevAppRunner] project dir not found: %s/%s",
            dev_install.source_owner,
            dev_install.source_repo,
        )
        return {}

    fn_name = _infer_function_name(dev_install)

    input_data = {
        "function": fn_name,
        "username": username,
        "project_id": project_id,
        "project_slug": project_slug,
        "get_params": get_params or {},
    }

    # Write runner script to project_dir so it is visible inside the container
    runner_dest = project_dir / ".scitex_run_dev_context.py"
    runner_in_container = "/workspace/.scitex_run_dev_context.py"

    try:
        runner_dest.write_text(
            _RUNNER_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8"
        )
    except Exception as exc:
        logger.error("[DevAppRunner] failed to write runner script: %s", exc)
        return {}

    module_name = dev_install.module_name
    app_env = {"SCITEX_CURRENT_APP": module_name}

    inner_cmd = [
        "env",
        f"SCITEX_CURRENT_APP={module_name}",
        "python",
        runner_in_container,
    ]

    try:
        job_ids = Allocation.find_existing_jobs(username)

        if job_ids:
            job_id = job_ids[0]
            instance = _instance_name(username)
            logger.info(
                "[DevAppRunner] reusing allocation job=%s instance=%s for %s",
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
                "[DevAppRunner] no active allocation for %s — using local apptainer exec",
                username,
            )
            # Per-app container takes priority over user default
            container = getattr(
                dev_install, "apptainer_container_path", ""
            ) or get_container_for_user(username)
            cmd = build_apptainer_exec_cmd(
                inner_cmd, project_dir, env_vars=app_env, container_path=container
            )

        logger.debug("[DevAppRunner] cmd: %s", " ".join(cmd))

        start = time.time()
        proc = subprocess.run(
            cmd,
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.time() - start

        if proc.returncode != 0:
            logger.warning(
                "[DevAppRunner] runner exited %d in %.1fs: %s",
                proc.returncode,
                elapsed,
                proc.stderr[:200],
            )
            return {}

        output = proc.stdout.strip()
        if not output:
            return {}

        result = json.loads(output)
        if not result.get("success"):
            logger.warning(
                "[DevAppRunner] context builder error: %s", result.get("error")
            )
            return {}

        return result.get("context") or {}

    except subprocess.TimeoutExpired:
        logger.warning("[DevAppRunner] timed out after %ds", timeout)
        return {}
    except FileNotFoundError:
        logger.error(
            "[DevAppRunner] apptainer or srun not found"
            " — running context builder unsandboxed is not allowed"
        )
        return {}
    except Exception as exc:
        logger.error("[DevAppRunner] error: %s", exc, exc_info=True)
        return {}
    finally:
        try:
            runner_dest.unlink(missing_ok=True)
        except OSError:
            pass


def _infer_function_name(dev_install) -> str:
    """Infer the context builder function name from the module name."""
    # module_name: dev__owner__repo → repo → repo_name → build_repo_name_context
    repo = dev_install.source_repo.replace("-", "_").replace(" ", "_").lower()
    return f"build_{repo}_context"


# EOF
