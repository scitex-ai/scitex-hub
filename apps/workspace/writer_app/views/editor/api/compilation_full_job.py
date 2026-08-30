#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The background worker behind ``POST /compile_full/``.

Extracted from ``compilation.py`` (which re-exports every name here, so
existing imports are unaffected) because the full-compile job is a
distinct responsibility from the HTTP views around it, and because that
module was 505 lines against a 512-line ceiling.

Three production defects live in this file's history:

1. **The script path was assembled by hand.** ``script_map`` hardcoded
   ``scripts/shell/compile_manuscript.sh`` and the runner exec'd
   ``bash /workspace/<that>``. But the apptainer runner binds the
   PROJECT ROOT as ``/workspace`` while scitex-writer vendors its
   scripts INSIDE the Writer workspace. The path was one segment too
   high, so every full compilation on scitex.ai returned::

       returncode 127
       /usr/bin/bash: /workspace/scripts/shell/compile_manuscript.sh:
       No such file or directory

   (measured on live prod 2026-08-17). The bind stays at the project
   root deliberately -- the compile script resolves its own
   ``PROJECT_ROOT`` from ``$(dirname $0)/../..``, i.e. the workspace, so
   it does not need to BE ``/workspace``; and binding the project root
   keeps project-level ``figures/`` and ``data/`` reachable. Only the
   path was wrong, and it now comes from the LEAF PACKAGE:
   ``scitex_writer.workspace_layout.compile_script`` (2.42.0+). Hub does
   not know the layout and must not learn it again.

2. **The compiled PDF was looked for at the wrong root.** The same
   off-by-one, one directory further on: ``config_manuscript.yaml`` pins
   ``paths.compiled_pdf: ./01_manuscript/manuscript.pdf`` relative to
   the WORKSPACE (which the script resolves as its own PROJECT_ROOT),
   while this module looked under ``project_dir/``. Fixing only the
   script path would therefore have produced a green compile reporting
   NO PDF FOUND.

3. **Failures carried no stated reason.** ``final_result`` was built
   with no ``error`` key at all, while the front-end reads
   ``data.result?.error || "Compilation failed"``
   (compilation-queue.ts). So the headline was always the generic
   fallback and the real cause sat in the log body. It now runs through
   the same :func:`_ensure_error_and_log` precedence the preview path
   uses, so preview and full behave identically.
"""

from __future__ import annotations

import logging
from pathlib import Path

from scitex_writer.workspace_layout import compile_script

from apps.infra.project_app.services.writer_workspace_layout import (
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


class CompileScriptMissing(FileNotFoundError):
    """The compile script scitex-writer names is not on disk.

    Its own class so a caller can tell "the workspace was never
    initialised" apart from "the project directory is gone".
    """


def _resolve_project_dir(project, user):
    """Resolve the host filesystem path of a writer project directory."""
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


def resolve_compile_script(project_dir, doc_type: str) -> Path:
    """Host path of ``doc_type``'s compile script, or fail naming both roots.

    ``scitex_writer.workspace_layout.compile_script`` deliberately does
    NOT existence-check -- it composes a path and says so. Hub is the side
    that EXECUTES the result, so hub is where a missing script has to be
    reported, and reported with enough to act on.

    That is the whole point of raising here rather than letting bash do
    it. The measured production message was::

        /usr/bin/bash: /workspace/scripts/shell/compile_manuscript.sh:
        No such file or directory

    which names the symptom and hides the two things needed to diagnose
    it: which project root the caller was holding, and therefore which of
    the two roots the path was composed against. The message below names
    both, so the same defect would read as its own explanation.

    Raises
    ------
    ValueError
        Propagated from the leaf package for an unknown ``doc_type``; it
        names the valid set. Not swallowed into a silent
        fall-back-to-manuscript, which would compile the wrong document
        and call it success.
    CompileScriptMissing
        When the composed path does not exist.
    """
    project_dir = Path(project_dir)
    script_path = compile_script(project_dir, doc_type)
    if not script_path.is_file():
        raise CompileScriptMissing(
            f"Writer compile script not found: {script_path} "
            f"(doc_type={doc_type!r}, project root={project_dir}). "
            "scitex_writer.workspace_layout.compile_script() composed that "
            "path from the project root named above; either the Writer "
            "workspace under that root was never initialised, or the "
            "project root is not the one you think it is. Executing it "
            "anyway is what produced 'bash: ...: No such file or "
            "directory' (rc 127) for every user on scitex.ai -- a message "
            "that names the symptom but not the root it came from."
        )
    return script_path


def container_script_path(project_dir, script_path) -> str:
    """``script_path`` as seen from inside the sandbox.

    The runner binds ``project_dir`` at :data:`CONTAINER_PROJECT_ROOT`, so
    the in-container path is that mount point plus the script's path
    RELATIVE TO THE BOUND DIRECTORY. Deriving the tail with
    ``relative_to`` rather than re-joining known segments is what keeps
    the layout knowledge in scitex-writer: if the leaf package moves the
    scripts, this still produces the right container path with no change
    here.
    """
    relpath = Path(script_path).relative_to(Path(project_dir)).as_posix()
    return f"{CONTAINER_PROJECT_ROOT}/{relpath}"


def build_inner_cmd(project_dir, doc_type: str, comp_options: dict) -> list:
    """The ``bash <script> <flags...>`` argv run inside the sandbox.

    Split out from :func:`run_compilation_async` so the path this file
    exists to get right can be asserted against a real on-disk workspace,
    without a Django request, a database, or an apptainer runtime.
    """
    script_path = resolve_compile_script(project_dir, doc_type)

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

    return ["bash", container_script_path(project_dir, script_path)] + flags


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


def locate_compiled_pdf(project_dir):
    """The PDF a full compilation wrote, or ``None``.

    The workspace location comes first because that is where the script
    writes (see defect 2 in the module docstring). The two project-root
    spellings stay as fallbacks for pre-workspace projects.
    """
    project_dir = Path(project_dir)
    candidates = [
        get_compiled_pdf_path(project_dir),
        project_dir / "01_manuscript" / "manuscript.pdf",
        project_dir / "manuscript.pdf",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


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

        inner_cmd = build_inner_cmd(project_dir, doc_type, comp_options)

        result = run_in_user_allocation(
            username=user.username,
            inner_cmd=inner_cmd,
            project_dir=project_dir,
            timeout=timeout,
            log_callback=on_log,
        )

        logger.info("[CompileFullAPI %s] Result: success=%s", job_id, result["success"])

        pdf_url = None
        if result["success"]:
            candidate = locate_compiled_pdf(project_dir)
            if candidate is not None:
                pdf_url = f"/apps/writer/api/project/{project_id}/pdf/{candidate.name}"

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
