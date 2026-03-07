#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04 20:46:58 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/views/index/main.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/writer_app/views/index/main.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""Main index view for SciTeX Writer - Simple editor/PDF viewer layout."""

import json
import logging

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render

from apps.project_app.models import Project
from apps.project_app.services import get_current_project

from ...models import Manuscript

logger = logging.getLogger(__name__)


def build_writer_context(request, current_project=None):
    """Build writer-specific template context for both full page and partial views."""
    document_type = request.GET.get("doc_type", "manuscript")
    valid_doc_types = ["manuscript", "shared", "supplementary", "revision"]
    if document_type not in valid_doc_types:
        document_type = "manuscript"

    context = {
        # is_visitor handled by context processor
        "writer_initialized": False,
        "document_type": document_type,
    }

    if not request.user.is_authenticated:
        return context

    if request.user.username.startswith("visitor-"):
        context["is_demo"] = True
        context["visitor_username"] = request.user.username

    user_projects = Project.objects.filter(owner=request.user).order_by("name")
    context["user_projects"] = user_projects

    if current_project is None:
        current_project = get_current_project(request, user=request.user)

    if current_project:
        context["current_project"] = current_project
        context["project"] = current_project

        manuscript, created = Manuscript.objects.get_or_create(
            project=current_project,
            defaults={
                "owner": current_project.owner,
                "title": f"{current_project.name} Manuscript",
                "description": f"Manuscript for {current_project.name}",
            },
        )

        if not manuscript.writer_initialized:
            from apps.project_app.services.project_filesystem import (
                get_project_filesystem_manager,
            )

            manager = get_project_filesystem_manager(request.user)
            project_root = manager.get_project_root_path(current_project)
            if project_root:
                manuscript_dir = project_root / "scitex" / "writer" / "01_manuscript"
                if not manuscript_dir.exists():
                    # App projects: show init instruction instead of auto-creating
                    if getattr(current_project, "is_app", False):
                        context["needs_writer_init"] = True
                    else:
                        try:
                            from scitex.writer import ensure_workspace

                            ensure_workspace(str(project_root))
                            logger.info(
                                f"Auto-initialized writer workspace for: {current_project.slug}"
                            )
                        except Exception as e:
                            logger.warning(f"Failed to auto-initialize writer: {e}")

        context["manuscript"] = manuscript
        context["manuscript_id"] = manuscript.id
        context["writer_initialized"] = manuscript.writer_initialized
    else:
        context["needs_project_creation"] = True

    return context


def index_view(request):
    """SciTeX Writer main page - Simple editor with PDF viewer."""
    if not request.user.is_authenticated:
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        is_browser = any(
            browser in user_agent
            for browser in ["Mozilla", "Chrome", "Safari", "Firefox", "Edge", "Opera"]
        )

        if is_browser:
            logger.info(
                "[Writer] Browser request not authenticated - redirecting to visitor-pool-full"
            )
            return redirect("public_app:visitor_pool_full")

        return render(
            request,
            "writer_app/index.html",
            {"is_visitor": True, "writer_initialized": False},
        )

    context = build_writer_context(request)
    return render(request, "writer_app/index.html", context)


def initialize_workspace(request):
    """Initialize Writer workspace for a project.

    Supports both authenticated users and visitor visitors.

    POST body:
        {
            "project_id": <project_id>
        }
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")

        if not project_id:
            return JsonResponse(
                {"success": False, "error": "project_id required"}, status=400
            )

        # Get effective user (authenticated or visitor)
        if request.user.is_authenticated:
            user = request.user
        else:
            # Get visitor user from session
            visitor_user_id = request.session.get("visitor_user_id")
            if not visitor_user_id:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Invalid session. Please refresh the page.",
                    },
                    status=403,
                )
            try:
                user = User.objects.get(id=visitor_user_id)
            except User.DoesNotExist:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Visitor user not found. Please refresh the page.",
                    },
                    status=403,
                )

        # Verify project access
        project = Project.objects.get(id=project_id, owner=user)

        # Ensure project directory exists (required for Writer initialization)
        from apps.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(user)
        project_root = manager.get_project_root_path(project)

        if not project_root:
            # Create project directory if it doesn't exist
            logger.info(f"Creating project directory for project {project_id}")
            success, project_root = manager.create_project_directory(
                project, use_template=False
            )
            if not success or not project_root:
                return JsonResponse(
                    {"success": False, "error": "Failed to create project directory"},
                    status=500,
                )
            logger.info(f"Project directory created at {project_root}")

        # Get or create manuscript
        # Since project is OneToOneField, only use project for lookup
        manuscript, created = Manuscript.objects.get_or_create(
            project=project,
            defaults={"owner": project.owner, "title": f"{project.name} Manuscript"},
        )

        # Check if Writer already initialized
        if manuscript.writer_initialized:
            return JsonResponse(
                {
                    "success": True,
                    "message": "Writer workspace already initialized",
                    "manuscript_id": manuscript.id,
                }
            )

        # Initialize Writer (creates directory structure using scitex.writer.Writer)
        from ...services import WriterService

        try:
            # Create WriterService - this initializes Writer() which creates the complete structure
            writer_service = WriterService(project_id, user.id)

            # Access the writer property - this triggers initialization if not done
            writer = writer_service.writer

            # Verify the structure was created
            if writer_service.writer_dir.exists():
                manuscript_dir = writer_service.writer_dir / "01_manuscript"
                if manuscript_dir.exists():
                    logger.info(
                        f"Writer workspace initialized successfully for project {project_id}"
                    )
                    logger.info(f"  Structure: {writer_service.writer_dir}")
                    logger.info(
                        f"Manuscript {manuscript.id} writer_initialized is now auto-detected as True"
                    )
                else:
                    raise Exception(
                        "Writer structure incomplete - 01_manuscript not found"
                    )
            else:
                raise Exception(
                    f"Writer directory not created at {writer_service.writer_dir}"
                )

        except Exception as e:
            logger.error(f"Failed to initialize writer workspace: {e}", exc_info=True)
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Failed to initialize Writer: {str(e)}",
                },
                status=500,
            )

        return JsonResponse(
            {
                "success": True,
                "message": "Writer workspace initialized",
                "manuscript_id": manuscript.id,
            }
        )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
