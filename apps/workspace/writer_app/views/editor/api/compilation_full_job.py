#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The background worker behind ``POST /compile_full/``.

Extracted from ``compilation.py`` (which re-exports every name here, so
existing imports are unaffected) because the full-compile job is a
distinct responsibility from the HTTP views around it, and because that
module hit its line ceiling.

Two production defects live in this file's history and both are guarded
by tests now:

1. **The script path was assembled by hand.** ``script_map`` hardcoded
   ``scripts/shell/compile_manuscript.sh`` and the runner exec'd
   ``bash /workspace/<that>``. But the apptainer runner binds the
   PROJECT ROOT as ``/workspace`` while scitex-writer vendors its
   scripts INSIDE the Writer workspace, at
   ``<project>/.scitex/writer/scripts/shell/``. The path was one level
   too high, so every full compilation on scitex.ai returned::

       returncode 127
       /usr/bin/bash: /workspace/scripts/shell/compile_manuscript.sh:
       No such file or directory

   (measured on live prod 2026-08-17). The bind stays at the project
   root deliberately — the compile script resolves its own
   ``PROJECT_ROOT`` from ``$(dirname $0)/../..``, i.e. the workspace, so
   it does not need to BE ``/workspace``; and binding the project root
   keeps project-level ``figures/`` and ``data/`` reachable. Only the
   path was wrong, and it now comes from the layout SSoT.

2. **Failures carried no stated reason.** ``final_result`` was built
   with no ``error`` key at all, while the front-end reads
   ``data.result?.error || "Compilation failed"``
   (compilation-queue.ts). So the headline was always the generic
   fallback and the real cause sat in the log body. It now runs through
   the same :func:`_ensure_error_and_log` precedence the preview path
   uses, so preview and full behave identically.
"""

from __future__ import annotations

import logging

from apps.infra.project_app.services.writer_workspace_layout import (
    get_compile_script_relpath,
    get_compiled_pdf_path,
)
from apps.workspace.console_app.services.apptainer_runner import run_in_user_allocation
from apps.workspace.writer_app.services.writer.compile_error import (
    _ensure_error_and_log,
)

logger = logging.getLogger(__name__)

# In-memory compilation job storage
# Format: {job_id: {'status': str, 'progress': int, 'step': str, 'log': list, 'result': dict}}
COMPILATION_JOBS = {}

# The project root is bound here inside the sandbox by
# ``apptainer_runner.build_apptainer_exec_cmd``.
CONTAINER_PROJECT_ROOT = "/workspace"


def _resolve_project_dir(project, user) -> "Path | None":  # noqa: F821
    """Resolve the host filesystem path of a writer project directory."""
    from pathlib import Path

    from django.conf import settings

    # Standard layout: data/users/<username>/proj/<slug>/
    base = Path(settings.BASE_DIR) / "data" / "users" / user.username / "proj"
    candidate = base / project.slug
    if candidate.is_dir():
        return candidate

    # Fallback: check MEDIA_ROOT / users / user_id
    media_base = Path(settings.MEDIA_ROOT) / "users" / str(user.id)
    candidate2 = media_base / "proj" / project.slug
    if candidate2.is_dir():
        return candidate2

    return None


def build_inner_cmd(doc_type: str, comp_options: dict) -> list:
    """The ``bash <script> <flags...>`` argv run inside the sandbox.

    Split out from :func:`run_compilation_async` so the path this file
    exists to get right can be asserted without a Django request, a real
    project on disk, or an apptainer runtime.
    """
    script_rel = get_compile_script_relpath(doc_type)

    flags = []
    if comp_options.get("no_figs"):
        flags.append("--no-figs")
    if comp_options.get("quiet"):
        flags.append("--quiet")
    if comp_options.get("verbose"):
        flags.append("--verbose")
    if comp_options.get("force"):
        flags.append("--force")
    if comp_options.get("track_changes"):
        flags.append("--track-changes")
    color = comp_options.get("color_mode", "light")
    if color:
        flags.extend(["--color-mode", color])

    return ["bash", f"{CONTAINER_PROJECT_ROOT}/{script_rel}"] + flags


def build_final_result(result: dict, pdf_url) -> dict:
    """Shape a runner result for the polling endpoint, reason included.

    ``_ensure_error_and_log`` is the SAME function the preview path
    calls, so a full-compile failure now reaches the user with the same
    precedence a preview failure does: the engine's first ``! ...`` line,
    else a collected error, else the exit-code message. Before this, a
    full-compile failure had no ``error`` key at all.
    """
    returncode = result.get("returncode")
    final_result = _ensure_error_and_log(
        {
            "success": result.get("success", False),
            "stdout": result.get("stdout"),
            "stderr": result.get("stderr"),
            "returncode": returncode,
            "message": f"Full compilation failed with exit code {returncode}",
        }
    )
    final_result["output_pdf"] = pdf_url
    final_result["pdf_path"] = pdf_url
    return final_result


def run_compilation_async(
    job_id, project_id, doc_type, timeout, user_id, comp_options=None
):
    """Run compilation in background thread — inside Apptainer sandbox."""
    try:
        from django.contrib.auth import get_user_model

        from apps.infra.project_app.models import Project

        User = get_user_model()
        project = Project.objects.get(id=project_id)
        user = User.objects.get(id=user_id)

        comp_options = comp_options or {}

        # Resolve host project directory
        project_dir = _resolve_project_dir(project, user)
        if not project_dir or not project_dir.is_dir():
            raise FileNotFoundError(
                f"Project directory not found for {user.username}/{project.slug}"
            )

        # Callbacks
        def on_log(message):
            if job_id in COMPILATION_JOBS:
                COMPILATION_JOBS[job_id]["log"].append(message)
            logger.debug("[Compilation %s] %s", job_id, message)

        if job_id in COMPILATION_JOBS:
            COMPILATION_JOBS[job_id]["status"] = "running"
            COMPILATION_JOBS[job_id]["step"] = "Starting compilation in sandbox..."

        inner_cmd = build_inner_cmd(doc_type, comp_options)

        result = run_in_user_allocation(
            username=user.username,
            inner_cmd=inner_cmd,
            project_dir=project_dir,
            timeout=timeout,
            log_callback=on_log,
        )

        logger.info("[CompileFullAPI %s] Result: success=%s", job_id, result["success"])

        # Locate output PDF. The compile script writes it INSIDE the Writer
        # workspace (config_manuscript.yaml pins
        # paths.compiled_pdf: ./01_manuscript/manuscript.pdf, relative to the
        # workspace it resolves as its own PROJECT_ROOT), so the workspace
        # path is checked first. The two project-root spellings are kept as
        # fallbacks for pre-.scitex/writer projects.
        pdf_url = None
        if result["success"]:
            pdf_candidates = [
                get_compiled_pdf_path(project_dir),
                project_dir / "01_manuscript" / "manuscript.pdf",
                project_dir / "manuscript.pdf",
            ]
            for candidate in pdf_candidates:
                if candidate.exists():
                    pdf_url = (
                        f"/apps/writer/api/project/{project_id}/pdf/{candidate.name}"
                    )
                    break

        final_result = build_final_result(result, pdf_url)

        if job_id in COMPILATION_JOBS:
            COMPILATION_JOBS[job_id]["status"] = (
                "completed" if result["success"] else "failed"
            )
            COMPILATION_JOBS[job_id]["progress"] = 100
            COMPILATION_JOBS[job_id]["step"] = (
                "Complete!" if result["success"] else "Failed"
            )
            COMPILATION_JOBS[job_id]["result"] = final_result

    except Exception as e:
        logger.error("[CompileFullAPI %s] Error: %s", job_id, e, exc_info=True)
        if job_id in COMPILATION_JOBS:
            COMPILATION_JOBS[job_id]["status"] = "failed"
            COMPILATION_JOBS[job_id]["step"] = "Error"
            COMPILATION_JOBS[job_id]["log"].append(f"[ERROR] {str(e)}")
            COMPILATION_JOBS[job_id]["result"] = {
                "success": False,
                "error": str(e),
                "log": str(e),
            }


# EOF
