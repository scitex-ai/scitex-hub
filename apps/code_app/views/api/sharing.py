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


class NotebookSharingAPI(NotebookAPIView):
    """API for notebook sharing."""

    def post(self, request, notebook_id):
        """Share notebook with other users."""
        try:
            data = json.loads(request.body)
            usernames = data.get("usernames", [])
            is_public = data.get("is_public", False)

            manager = self.get_notebook_manager()
            notebook = manager.load_notebook(notebook_id)

            if not notebook:
                return JsonResponse(
                    {"status": "error", "message": "Notebook not found"}, status=404
                )

            # Update public status
            notebook.is_public = is_public

            # Share with specific users
            if usernames:
                from django.contrib.auth.models import User

                users = User.objects.filter(username__in=usernames)
                notebook.shared_with.set(users)

            notebook.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Notebook sharing updated",
                    "shared_with": [
                        user.username for user in notebook.shared_with.all()
                    ],
                    "is_public": notebook.is_public,
                }
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON"}, status=400
            )
        except Exception as e:
            logger.error(f"Error sharing notebook {notebook_id}: {e}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


# EOF
