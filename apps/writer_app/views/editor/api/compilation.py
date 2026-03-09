#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/views/editor/api/compilation.py
"""Compilation endpoints - preview and full compilation."""

from __future__ import annotations

import json
import logging
import threading
import uuid

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.console_app.services.apptainer_runner import run_in_user_allocation

from ..auth_utils import api_login_optional, get_user_for_request

logger = logging.getLogger(__name__)

# In-memory compilation job storage
# Format: {job_id: {'status': str, 'progress': int, 'step': str, 'log': list, 'result': dict}}
COMPILATION_JOBS = {}


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
        from apps.project_app.models import Project

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

        # Compile preview
        result = writer_service.compile_preview(
            latex_content=content,
            timeout=60,
            color_mode=color_mode,
            section_name=section_name,
            doc_type=doc_type,
        )

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
        from apps.project_app.models import Project

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


def _resolve_project_dir(project, user) -> "Path | None":
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


def run_compilation_async(
    job_id, project_id, doc_type, timeout, user_id, comp_options=None
):
    """Run compilation in background thread — inside Apptainer sandbox."""
    try:
        from django.contrib.auth import get_user_model

        from apps.project_app.models import Project

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

        # Map doc_type to compile script (relative to project root)
        script_map = {
            "manuscript": "scripts/shell/compile_manuscript.sh",
            "supplementary": "scripts/shell/compile_supplementary.sh",
            "revision": "scripts/shell/compile_revision.sh",
        }
        script_rel = script_map.get(doc_type, "scripts/shell/compile_manuscript.sh")

        # Callbacks
        def on_log(message):
            if job_id in COMPILATION_JOBS:
                COMPILATION_JOBS[job_id]["log"].append(message)
            logger.debug("[Compilation %s] %s", job_id, message)

        def on_progress(percent, step):
            if job_id in COMPILATION_JOBS:
                COMPILATION_JOBS[job_id]["progress"] = percent
                COMPILATION_JOBS[job_id]["step"] = step
                COMPILATION_JOBS[job_id]["status"] = "running"

        if job_id in COMPILATION_JOBS:
            COMPILATION_JOBS[job_id]["status"] = "running"
            COMPILATION_JOBS[job_id]["step"] = "Starting compilation in sandbox..."

        # Build options flags for the shell script
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

        inner_cmd = ["bash", f"/workspace/{script_rel}"] + flags

        result = run_in_user_allocation(
            username=user.username,
            inner_cmd=inner_cmd,
            project_dir=project_dir,
            timeout=timeout,
            log_callback=on_log,
        )

        logger.info("[CompileFullAPI %s] Result: success=%s", job_id, result["success"])

        # Locate output PDF
        pdf_url = None
        if result["success"]:
            pdf_candidates = [
                project_dir / "01_manuscript" / "manuscript.pdf",
                project_dir / "manuscript.pdf",
            ]
            for candidate in pdf_candidates:
                if candidate.exists():
                    pdf_url = (
                        f"/apps/writer/api/project/{project_id}/pdf/{candidate.name}"
                    )
                    break

        final_result = {
            "success": result["success"],
            "log": result["stdout"],
            "output_pdf": pdf_url,
            "pdf_path": pdf_url,
            "returncode": result["returncode"],
        }

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
    from apps.writer_app.utils.ansi_to_html import ansi_to_html

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
