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


class NotebookExecutionAPI(NotebookAPIView):
    """API for notebook execution."""

    def post(self, request, notebook_id):
        """Execute a notebook or specific cell."""
        try:
            data = json.loads(request.body)
            cell_index = data.get("cell_index")  # If specified, execute only this cell
            timeout = min(int(data.get("timeout", 300)), 600)
            memory_limit = min(int(data.get("memory_limit", 512)), 2048)

            manager = self.get_notebook_manager()
            notebook = manager.load_notebook(notebook_id)

            if not notebook:
                return JsonResponse(
                    {"status": "error", "message": "Notebook not found"}, status=404
                )

            # Create execution job
            job = CodeExecutionJob.objects.create(
                user=request.user,
                execution_type="notebook",
                source_code=f"Notebook: {notebook.title}",
                timeout_seconds=timeout,
                max_memory_mb=memory_limit,
            )

            executor = NotebookExecutor(timeout=timeout, memory_limit=memory_limit)

            if cell_index is not None:
                # Execute single cell
                def execute_cell():
                    success, result = executor.execute_cell(notebook, cell_index)

                    job.status = "completed" if success else "failed"
                    job.completed_at = timezone.now()
                    if success:
                        job.output = json.dumps(result, indent=2)
                    else:
                        job.error_output = result.get("error", "Unknown error")
                    job.save()

                execution_thread = threading.Thread(target=execute_cell)
                execution_thread.daemon = True
                execution_thread.start()

                return JsonResponse(
                    {
                        "status": "success",
                        "message": f"Cell {cell_index} execution started",
                        "job_id": str(job.job_id),
                        "execution_type": "cell",
                    }
                )

            else:
                # Execute entire notebook
                def execute_notebook():
                    executor.execute_notebook(notebook, job)

                execution_thread = threading.Thread(target=execute_notebook)
                execution_thread.daemon = True
                execution_thread.start()

                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Notebook execution started",
                        "job_id": str(job.job_id),
                        "execution_type": "notebook",
                    }
                )

        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON"}, status=400
            )
        except Exception as e:
            logger.error(f"Error executing notebook {notebook_id}: {e}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


# EOF
