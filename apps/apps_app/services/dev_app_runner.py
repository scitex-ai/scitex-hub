#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DevAppRunner — executes dev app context builders inside Apptainer.

Prevents dev app backend code from running inside the Django process.
Uses JSON stdin/stdout protocol with run_dev_context.py as the sandboxed runner.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Path to the runner script (inside Django container, bind-mounted into Apptainer)
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

    The dev app directory is bound to /workspace. The runner script
    imports views.py from /workspace, calls the context builder,
    and returns JSON context.

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
    from apps.apps_app.services.dev_app_loader import resolve_dev_project_dir
    from apps.console_app.services.apptainer_runner import _get_container_path

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

    # Derive context builder function name from module name
    fn_name = _infer_function_name(dev_install)

    input_data = {
        "function": fn_name,
        "username": username,
        "project_id": project_id,
        "project_slug": project_slug,
        "get_params": get_params or {},
    }

    container = _get_container_path()

    # The runner script needs to be visible inside the container.
    # Bind-mount it as a read-only file at a known path.
    runner_script_host = str(_RUNNER_SCRIPT.resolve())
    runner_in_container = "/tmp/_scitex_run_dev_context.py"

    cmd = [
        "apptainer",
        "exec",
        "--contain",
        "--cleanenv",
        "--no-home",
        "--bind",
        f"{project_dir}:/workspace:rw",
        "--bind",
        f"{runner_script_host}:{runner_in_container}:ro",
        container,
        "python",
        runner_in_container,
    ]

    logger.debug("[DevAppRunner] cmd: %s", " ".join(cmd))

    start = time.time()
    try:
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
            "[DevAppRunner] apptainer not found"
            " — running context builder unsandboxed is not allowed"
        )
        return {}
    except Exception as exc:
        logger.error("[DevAppRunner] error: %s", exc, exc_info=True)
        return {}


def _infer_function_name(dev_install) -> str:
    """Infer the context builder function name from the module name."""
    # module_name: dev__owner__repo → repo → repo_name → build_repo_name_context
    repo = dev_install.source_repo.replace("-", "_").replace(" ", "_").lower()
    return f"build_{repo}_context"


# EOF
