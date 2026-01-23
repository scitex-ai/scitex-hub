#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/views/editor/api/compilation.py
"""Compilation endpoints - preview and full compilation."""

from __future__ import annotations
import json
import logging
import uuid
import threading
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
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
        from ....services import WriterService
        from apps.project_app.models import Project

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
            # To URL: /writer/api/project/101/pdf/preview-abstract-light.pdf
            pdf_filename = pdf_path.name
            result["output_pdf"] = (
                f"/writer/api/project/{project_id}/pdf/{pdf_filename}"
            )
            logger.info(
                f"[CompileAPI] Converted PDF path to URL: {result['output_pdf']}"
            )
            logger.info(
                f"[CompileAPI] Note: Alternate theme will be compiled in background for instant switching"
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

        # Extract compilation options
        comp_options = {
            "no_figs": data.get("no_figs", False),
            "ppt2tif": data.get("ppt2tif", False),
            "crop_tif": data.get("crop_tif", False),
            "quiet": data.get("quiet", False),
            "verbose": data.get("verbose", False),
            "force": data.get("force", False),
            "track_changes": data.get("track_changes", False),
        }

        logger.info(f"[CompileFullAPI] project_id={project_id}, doc_type={doc_type}")

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


def run_compilation_async(
    job_id, project_id, doc_type, timeout, user_id, comp_options=None
):
    """Run compilation in background thread with job tracking"""
    try:
        from ....services import WriterService

        writer_service = WriterService(project_id, user_id)
        comp_options = comp_options or {}

        # Define callbacks to update job state
        def on_log(message):
            """Callback to collect logs in real-time"""
            if job_id in COMPILATION_JOBS:
                COMPILATION_JOBS[job_id]["log"].append(message)
            logger.debug(f"[Compilation {job_id}] {message}")

        def on_progress(percent, step):
            """Callback to track progress in real-time"""
            if job_id in COMPILATION_JOBS:
                COMPILATION_JOBS[job_id]["progress"] = percent
                COMPILATION_JOBS[job_id]["step"] = step
                COMPILATION_JOBS[job_id]["status"] = "running"
            logger.info(f"[Compilation {job_id}] {percent}% - {step}")

        # Call appropriate compilation method based on doc_type
        if doc_type == "manuscript":
            result = writer_service.compile_manuscript(
                timeout=timeout,
                log_callback=on_log,
                progress_callback=on_progress,
                no_figs=comp_options.get("no_figs", False),
                ppt2tif=comp_options.get("ppt2tif", False),
                crop_tif=comp_options.get("crop_tif", False),
                quiet=comp_options.get("quiet", False),
                verbose=comp_options.get("verbose", False),
                force=comp_options.get("force", False),
            )
        elif doc_type == "supplementary":
            result = writer_service.compile_supplementary(
                timeout=timeout,
                log_callback=on_log,
                progress_callback=on_progress,
                no_figs=comp_options.get("no_figs", False),
                ppt2tif=comp_options.get("ppt2tif", False),
                crop_tif=comp_options.get("crop_tif", False),
                quiet=comp_options.get("quiet", False),
            )
        elif doc_type == "revision":
            result = writer_service.compile_revision(
                timeout=timeout,
                log_callback=on_log,
                progress_callback=on_progress,
                track_changes=comp_options.get("track_changes", False),
            )
        else:
            raise ValueError(f"Invalid doc_type: {doc_type}")

        logger.info(
            f"[CompileFullAPI {job_id}] Result: success={result.get('success')}"
        )

        # Convert absolute filesystem path to servable URL
        if result.get("success") and result.get("output_pdf"):
            from pathlib import Path

            pdf_path = Path(result["output_pdf"])
            pdf_filename = pdf_path.name
            pdf_url = f"/writer/api/project/{project_id}/pdf/{pdf_filename}"
            result["output_pdf"] = pdf_url
            result["pdf_path"] = pdf_url
            logger.info(f"[CompileFullAPI {job_id}] PDF URL: {pdf_url}")

        # Update job with result
        if job_id in COMPILATION_JOBS:
            COMPILATION_JOBS[job_id]["status"] = (
                "completed" if result.get("success") else "failed"
            )
            COMPILATION_JOBS[job_id]["progress"] = 100
            COMPILATION_JOBS[job_id]["step"] = (
                "Complete!" if result.get("success") else "Failed"
            )
            COMPILATION_JOBS[job_id]["result"] = result

    except Exception as e:
        logger.error(f"[CompileFullAPI {job_id}] Error: {e}", exc_info=True)

        # Update job with error
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
    from ....utils.ansi_to_html import ansi_to_html

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
        }
    )


# View aliases for backward compatibility
compile_preview_view = compile_api
compile_view = compile_api
preview_pdf_view = compile_api

# EOF
