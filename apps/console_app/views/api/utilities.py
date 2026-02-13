#!/usr/bin/env python3
"""
API views for SciTeX-Code Jupyter notebook integration.
"""

import json
import logging
import threading

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ...models import Notebook, CodeExecutionJob
from ...services.jupyter import (
    NotebookManager,
    NotebookExecutor,
    NotebookConverter,
    NotebookTemplates,
    NotebookValidator,
)

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class NotebookAPIView(View):
    """Base API view for notebook operations."""

    def get_notebook_manager(self):
        return NotebookManager(self.request.user)


def notebook_status_api(request, job_id):
    """Get notebook execution status via REST API."""
    try:
        job = CodeExecutionJob.objects.get(job_id=job_id, user=request.user)

        return Response(
            {
                "job_id": str(job.job_id),
                "status": job.status,
                "execution_type": job.execution_type,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "execution_time": job.execution_time,
                "cpu_time": job.cpu_time,
                "memory_peak": job.memory_peak,
                "output": json.loads(job.output) if job.output else None,
                "error_output": job.error_output,
            }
        )

    except CodeExecutionJob.DoesNotExist:
        return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error getting job status {job_id}: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def duplicate_notebook_api(request, notebook_id):
    """Duplicate a notebook via REST API."""
    try:
        data = request.data
        new_title = data.get("title", "").strip()

        if not new_title:
            return Response(
                {"error": "New title is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        manager = NotebookManager(request.user)
        new_notebook = manager.duplicate_notebook(notebook_id, new_title)

        if not new_notebook:
            return Response(
                {"error": "Notebook not found or duplication failed"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "status": "success",
                "message": "Notebook duplicated successfully",
                "notebook": {
                    "id": str(new_notebook.notebook_id),
                    "title": new_notebook.title,
                    "description": new_notebook.description,
                    "status": new_notebook.status,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error duplicating notebook {notebook_id}: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# EOF
