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


class NotebookListAPI(NotebookAPIView):
    """API for listing and creating notebooks."""

    def get(self, request):
        """List user's notebooks."""
        try:
            notebooks = (
                Notebook.objects.filter(user=request.user)
                .prefetch_related("shared_with")
                .order_by("-updated_at")
            )

            # Pagination
            page = int(request.GET.get("page", 1))
            per_page = min(int(request.GET.get("per_page", 20)), 50)
            start = (page - 1) * per_page
            end = start + per_page

            paginated_notebooks = notebooks[start:end]

            notebooks_data = []
            for notebook in paginated_notebooks:
                notebooks_data.append(
                    {
                        "id": str(notebook.notebook_id),
                        "title": notebook.title,
                        "description": notebook.description,
                        "status": notebook.status,
                        "is_public": notebook.is_public,
                        "execution_count": notebook.execution_count,
                        "last_executed": notebook.last_executed.isoformat()
                        if notebook.last_executed
                        else None,
                        "created_at": notebook.created_at.isoformat(),
                        "updated_at": notebook.updated_at.isoformat(),
                        "cell_count": len(notebook.content.get("cells", [])),
                        "shared_with_count": notebook.shared_with.count(),
                    }
                )

            return JsonResponse(
                {
                    "status": "success",
                    "notebooks": notebooks_data,
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total": notebooks.count(),
                        "has_next": end < notebooks.count(),
                        "has_previous": page > 1,
                    },
                }
            )

        except Exception as e:
            logger.error(f"Error listing notebooks: {e}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    def post(self, request):
        """Create a new notebook."""
        try:
            data = json.loads(request.body)
            title = data.get("title", "").strip()
            description = data.get("description", "").strip()
            template = data.get("template", "blank")

            if not title:
                return JsonResponse(
                    {"status": "error", "message": "Title is required"}, status=400
                )

            # Check for duplicate titles
            if Notebook.objects.filter(user=request.user, title=title).exists():
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "A notebook with this title already exists",
                    },
                    status=400,
                )

            manager = self.get_notebook_manager()

            # Create notebook with template
            if template == "data_analysis":
                notebook_content = NotebookTemplates.get_data_analysis_template()
            elif template == "machine_learning":
                notebook_content = NotebookTemplates.get_machine_learning_template()
            elif template == "visualization":
                notebook_content = NotebookTemplates.get_visualization_template()
            else:
                # Create blank notebook
                notebook = manager.create_notebook(title, description)
                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Notebook created successfully",
                        "notebook": {
                            "id": str(notebook.notebook_id),
                            "title": notebook.title,
                            "description": notebook.description,
                            "status": notebook.status,
                        },
                    }
                )

            # Create notebook with template content
            notebook = Notebook.objects.create(
                user=request.user,
                title=title,
                description=description,
                content=notebook_content,
                status="draft",
            )

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Notebook created successfully",
                    "notebook": {
                        "id": str(notebook.notebook_id),
                        "title": notebook.title,
                        "description": notebook.description,
                        "status": notebook.status,
                        "template": template,
                    },
                }
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON"}, status=400
            )
        except Exception as e:
            logger.error(f"Error creating notebook: {e}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


# EOF
