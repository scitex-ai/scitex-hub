#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DevAppRunner — executes dev app context builders inside Apptainer.

Prevents dev app backend code from running inside the Django process.
Uses JSON stdin/stdout protocol with run_dev_context.py as the sandboxed runner.

Primary path: reuse the user's existing SLURM allocation via run_in_user_allocation.
A unique public helper is staged exclusively in project_dir and removed only
while its file identity still belongs to this call.
"""

from __future__ import annotations

import json
import logging
import os
import stat
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Path to the runner script (inside Django container, copied to project dir at runtime)
_RUNNER_SCRIPT = Path(__file__).parent.parent / "scripts" / "run_dev_context.py"


@contextmanager
def _owned_runner_file(project_dir: Path):
    """Stage public helper code exclusively; never overwrite project content."""
    content = _RUNNER_SCRIPT.read_text(encoding="utf-8")
    fd, filename = tempfile.mkstemp(
        prefix=".scitex_run_dev_context-", suffix=".py", dir=project_dir
    )
    path = Path(filename)
    identity = os.fstat(fd)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            # This public static script must be readable by the runtime UID.
            # Credentials and request data travel only through stdin.
            os.fchmod(stream.fileno(), 0o644)
        yield path
    finally:
        try:
            current = path.lstat()
            if stat.S_ISREG(current.st_mode) and (current.st_dev, current.st_ino) == (
                identity.st_dev,
                identity.st_ino,
            ):
                path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            logger.warning("[DevAppRunner] owned helper cleanup unavailable")


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

    A unique runtime-readable helper is staged under the validated project root.
    Request metadata and credentials use a JSON stdin envelope, never argv.

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
        logger.warning("[DevAppRunner] project directory unavailable")
        return {}

    payload = {
        "function": _infer_function_name(dev_install),
        "username": username,
        "project_id": project_id,
        "project_slug": project_slug,
        "get_params": get_params or {},
    }
    app_env = {
        "SCITEX_CURRENT_APP": dev_install.module_name,
        "SCITEX_API_TOKEN": _generate_api_token(username),
        "SCITEX_API_URL": os.environ.get("SCITEX_API_URL", "http://127.0.0.1:8000"),
    }

    try:
        with _owned_runner_file(project_dir) as runner_dest:
            # Only framework-owned executable/script names enter argv. Dynamic
            # metadata and credentials are initialized inside the sandbox.
            inner_cmd = ["python", f"/workspace/{runner_dest.name}"]
            job_ids = Allocation.find_existing_jobs(username)
            if job_ids:
                cmd = [
                    "srun",
                    "--overlap",
                    f"--jobid={job_ids[0]}",
                    "apptainer",
                    "instance",
                    "exec",
                    _instance_name(username),
                    *inner_cmd,
                ]
            else:
                container = getattr(
                    dev_install, "apptainer_container_path", ""
                ) or get_container_for_user(username)
                cmd = build_apptainer_exec_cmd(
                    inner_cmd, project_dir, container_path=container
                )

            start = time.time()
            proc = subprocess.run(
                cmd,
                input=json.dumps({"payload": payload, "app_env": app_env}),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            elapsed = time.time() - start
            if proc.returncode != 0:
                logger.warning(
                    "[DevAppRunner] runner exited %d in %.1fs",
                    proc.returncode,
                    elapsed,
                )
                return {}
            output = proc.stdout.strip()
            if not output:
                return {}
            result = json.loads(output)
            if not result.get("success"):
                logger.warning("[DevAppRunner] context builder returned an error")
                return {}
            return result.get("context") or {}
    except subprocess.TimeoutExpired:
        logger.warning("[DevAppRunner] context builder timed out")
        return {}
    except FileNotFoundError:
        logger.error("[DevAppRunner] sandbox runtime or helper unavailable")
        return {}
    except Exception:
        logger.error("[DevAppRunner] context builder failed")
        return {}


def _generate_api_token(username: str) -> str:
    """Generate a short-lived JWT for SDK access from Apptainer."""
    try:
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.tokens import RefreshToken

        User = get_user_model()
        user = User.objects.get(username=username)
        return str(RefreshToken.for_user(user).access_token)
    except Exception:
        logger.warning("[DevAppRunner] API token generation unavailable")
        return ""


def _infer_function_name(dev_install) -> str:
    """Infer the context builder function name from the module name."""
    # module_name: dev__owner__repo → repo → repo_name → build_repo_name_context
    repo = dev_install.source_repo.replace("-", "_").replace(" ", "_").lower()
    return f"build_{repo}_context"


# EOF
