#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-hub/apps/writer_app/views/editor/api/compilation.py
"""Compilation endpoints - preview and full compilation."""

from __future__ import annotations

import json
import logging
import threading
import uuid

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ..auth_utils import api_login_optional, get_user_for_request
from .compilation_full_job import (
    COMPILATION_JOBS,
    _resolve_project_dir,
    build_final_result,
    build_inner_cmd,
    run_compilation_async,
)

__all__ = [
    "COMPILATION_JOBS",
    "_resolve_project_dir",
    "build_final_result",
    "build_inner_cmd",
    "compilation_job_status",
    "compilation_status_api",
    "compile_api",
    "compile_full_view",
    "compile_preview_view",
    "compile_view",
    "preview_pdf_view",
    "run_compilation_async",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# G4 — server-side preview coalesce
# ---------------------------------------------------------------------------
# The UI's "Compile on Change" + multi-tab editing can fire several POSTs to
# compile_api for the SAME (project_id, section_name, color_mode) in quick
# succession. Daphne handles these concurrently in its sync threadpool, so
# multiple compile_content() invocations race on the SHARED destination
#   writer_dir/.preview/preview-<section>-<color>.pdf
# Without serialisation the racing `cp` step inside compile_content.sh
# propagates a non-zero exit and the UI surfaces it as the infamous
# "Compilation failed with exit code 12" error (see scitex.ai prod incident
# 2026-06-10 / lead diagnosis).
#
# We serialise per (project_id, section_name, color_mode) key with an
# in-process threading.Lock. Daphne in prod runs as a single asyncio process
# (see deployment/docker/docker_prod/docker-compose.yml), so an in-process
# Lock is sufficient. Different (project, section, colour) tuples continue
# to compile in parallel.
#
# Companion hardening lives in scitex-writer (G2 atomic cp+mv, G3 flock,
# G1 schema unification). This Django coalesce is the first/cheapest layer.
_PREVIEW_LOCKS: dict[tuple, threading.Lock] = {}
_PREVIEW_LOCKS_GUARD = threading.Lock()

# Bound the wait so a stuck/long compile doesn't tie up every Daphne worker.
# 65s = 60s preview compile timeout + 5s slack for queueing.
_PREVIEW_LOCK_WAIT_SECONDS = 65


def _get_preview_lock(
    project_id: int, section_name: str, color_mode: str
) -> threading.Lock:
    """Return (creating if necessary) the per-key preview lock.

    Lookup is guarded by ``_PREVIEW_LOCKS_GUARD`` so two threads that race
    on the same brand-new key both observe the same Lock instance.
    """
    key = (project_id, section_name, color_mode)
    with _PREVIEW_LOCKS_GUARD:
        lock = _PREVIEW_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _PREVIEW_LOCKS[key] = lock
        return lock


def _run_under_preview_lock(
    project_id: int,
    section_name: str,
    color_mode: str,
    fn,
    wait_seconds=None,
):
    """Serialise ``fn()`` per (project_id, section_name, color_mode).

    Returns the tuple ``("ok", fn_result)`` when the lock was acquired
    within ``wait_seconds`` (default ``_PREVIEW_LOCK_WAIT_SECONDS``) and the
    callable returned, or ``("busy", None)`` when the lock could not be
    acquired in time. The callable is invoked with no arguments and may
    raise; exceptions propagate after the lock is released.

    Extracted from ``compile_api`` so that the locking contract can be
    exercised in tests with a real callable (no monkeypatching of HTTP
    machinery), per the project's no-mock testing rule.
    """
    if wait_seconds is None:
        wait_seconds = _PREVIEW_LOCK_WAIT_SECONDS
    lock = _get_preview_lock(project_id, section_name, color_mode)
    acquired = lock.acquire(timeout=wait_seconds)
    if not acquired:
        return ("busy", None)
    try:
        return ("ok", fn())
    finally:
        lock.release()


@api_login_optional
@require_http_methods(["POST"])
def compile_api(request, project_id):
    """Compile LaTeX content to PDF.

    POST body:
        {
            "content": <latex_content>,
            "doc_type": "manuscript" (optional),
            "color_mode": "light" (optional: light, dark, sepia, paper),
            "section_name": <section_name> (optional, for naming)
        }
    """
    try:
        from apps.infra.project_app.models import Project

        from ....services import WriterService

        data = json.loads(request.body)
        content = data.get("content", "")
        doc_type = data.get("doc_type", "manuscript")
        color_mode = data.get("color_mode", "light")
        section_name = data.get("section_name", "preview")

        logger.info(
            f"[CompileAPI] project_id={project_id}, section={section_name}, color_mode={color_mode}"
        )

        # Get project and service
        project = Project.objects.get(id=project_id)

        # Get effective user (authenticated or visitor)
        user, is_visitor = get_user_for_request(request, project_id)
        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        writer_service = WriterService(project_id, user.id)

        # G4 — serialise same-key previews to prevent .preview/<name>.pdf
        # write race (root cause of historical "exit code 12" symptom).
        preview_lock = _get_preview_lock(project_id, section_name, color_mode)
        acquired = preview_lock.acquire(timeout=_PREVIEW_LOCK_WAIT_SECONDS)
        if not acquired:
            logger.warning(
                "[CompileAPI] Preview lock contention timeout "
                f"project={project_id} section={section_name} color={color_mode}"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": ("Preview compile is busy for this section, please retry"),
                },
                status=409,
            )

        try:
            # Compile preview (serialised per (project, section, colour))
            result = writer_service.compile_preview(
                latex_content=content,
                timeout=60,
                color_mode=color_mode,
                section_name=section_name,
                doc_type=doc_type,
            )
        finally:
            preview_lock.release()

        logger.info(f"[CompileAPI] Compilation result: success={result.get('success')}")

        # Convert absolute filesystem path to servable URL
        if result.get("success") and result.get("output_pdf"):
            from pathlib import Path

            pdf_path = Path(result["output_pdf"])
            # Convert: /app/data/users/USER/PROJECT/scitex/writer/.preview/preview-abstract-light.pdf
            # To URL: /apps/writer/api/project/101/pdf/preview-abstract-light.pdf
            pdf_filename = pdf_path.name
            result["output_pdf"] = (
                f"/apps/writer/api/project/{project_id}/pdf/{pdf_filename}"
            )
            logger.info(
                f"[CompileAPI] Converted PDF path to URL: {result['output_pdf']}"
            )
            logger.info(
                "[CompileAPI] Note: Alternate theme will be compiled in background for instant switching"
            )

        return JsonResponse(result)

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"Error compiling: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def compilation_status_api(request):
    """Get compilation job status.

    Query params:
        - job_id: Compilation job ID
    """
    try:
        from ....services import CompilerService

        job_id = request.GET.get("job_id")

        if not job_id:
            return JsonResponse(
                {"success": False, "error": "job_id required"}, status=400
            )

        # Get status via service
        compilation_service = CompilerService(None, request.user.id)
        status = compilation_service.get_status(job_id)

        return JsonResponse({"success": True, "status": status})

    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@api_login_optional
@require_http_methods(["POST"])
def compile_full_view(request, project_id):
    """Compile full manuscript from workspace files.

    POST body:
        {
            "doc_type": "manuscript|supplementary|revision",
            "timeout": 300 (optional),
            "color_mode": "light" (optional: light, dark),
            # Manuscript options:
            "no_figs": false,
            "ppt2tif": false,
            "crop_tif": false,
            "quiet": false,
            "verbose": false,
            "force": false,
            # Revision options:
            "track_changes": false
        }
    """
    try:
        from apps.infra.project_app.models import Project

        data = json.loads(request.body)
        doc_type = data.get("doc_type", "manuscript")
        timeout = data.get("timeout", 300)
        color_mode = data.get("color_mode", "light")

        # Extract compilation options
        comp_options = {
            "no_figs": data.get("no_figs", False),
            "ppt2tif": data.get("ppt2tif", False),
            "crop_tif": data.get("crop_tif", False),
            "quiet": data.get("quiet", False),
            "verbose": data.get("verbose", False),
            "force": data.get("force", False),
            "track_changes": data.get("track_changes", False),
            "color_mode": color_mode,
        }

        logger.info(
            f"[CompileFullAPI] project_id={project_id}, doc_type={doc_type}, color_mode={color_mode}"
        )

        # Get project and service
        project = Project.objects.get(id=project_id)

        # Get effective user (authenticated or visitor)
        user, is_visitor = get_user_for_request(request, project_id)
        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        # Create job ID for tracking
        job_id = str(uuid.uuid4())

        # Initialize job
        COMPILATION_JOBS[job_id] = {
            "status": "pending",
            "progress": 0,
            "step": "Initializing...",
            "log": [],
            "result": None,
            "project_id": project_id,
            "doc_type": doc_type,
            "color_mode": color_mode,
        }

        # Start compilation in background thread
        thread = threading.Thread(
            target=run_compilation_async,
            args=(job_id, project_id, doc_type, timeout, user.id, comp_options),
            daemon=True,
        )
        thread.start()

        # Return job ID immediately for polling
        return JsonResponse(
            {"success": True, "job_id": job_id, "message": "Compilation started"}
        )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[CompileFullAPI] Error: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@api_login_optional
@require_http_methods(["GET"])
def compilation_job_status(request, project_id, job_id):
    """Get compilation job status for polling."""
    if job_id not in COMPILATION_JOBS:
        return JsonResponse({"success": False, "error": "Job not found"}, status=404)

    job = COMPILATION_JOBS[job_id]

    # Check if job belongs to this project
    if job["project_id"] != project_id:
        return JsonResponse(
            {"success": False, "error": "Job not found for this project"}, status=404
        )

    # Convert ANSI codes to HTML
    from apps.workspace.writer_app.utils.ansi_to_html import ansi_to_html

    raw_log = "\n".join(job["log"])
    html_log = ansi_to_html(raw_log)

    return JsonResponse(
        {
            "success": True,
            "status": job["status"],
            "progress": job["progress"],
            "step": job["step"],
            "log": raw_log,  # Plain text for parsing
            "log_html": html_log,  # HTML with colors
            "result": job["result"],
            "color_mode": job.get("color_mode", "light"),
        }
    )


# View aliases for backward compatibility
compile_preview_view = compile_api
compile_view = compile_api
preview_pdf_view = compile_api

# EOF
