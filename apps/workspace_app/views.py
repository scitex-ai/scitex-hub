#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-14 20:15:00 (ywatanabe)"
# File: ./apps/workspace_app/views.py

"""
User workspace views

Provides web interface for managing user containers.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .services import UserContainerManager


@login_required
def workspace_dashboard(request):
    """
    Workspace dashboard showing container status and controls
    """
    manager = UserContainerManager()

    # Get workspace status
    status = manager.get_container_status(request.user)

    # Get workspace record
    from .models import UserWorkspace

    try:
        workspace = UserWorkspace.objects.get(user=request.user)
    except UserWorkspace.DoesNotExist:
        workspace = None

    context = {
        "status": status,
        "workspace": workspace,
        "is_running": status is not None and status.get("status") == "running",
    }

    return render(request, "workspace_app/dashboard.html", context)


@login_required
def start_workspace(request):
    """Start user's workspace container"""
    if request.method == "POST":
        manager = UserContainerManager()

        try:
            container = manager.get_or_create_container(request.user)
            messages.success(
                request, f"Workspace started successfully! Container: {container.name}"
            )
        except Exception as e:
            messages.error(request, f"Failed to start workspace: {str(e)}")

    return redirect("workspace_app:dashboard")


@login_required
def stop_workspace(request):
    """Stop user's workspace container"""
    if request.method == "POST":
        manager = UserContainerManager()

        try:
            if manager.stop_container(request.user):
                messages.success(request, "Workspace stopped successfully")
            else:
                messages.info(request, "No running workspace found")
        except Exception as e:
            messages.error(request, f"Failed to stop workspace: {str(e)}")

    return redirect("workspace_app:dashboard")


@login_required
def workspace_status_api(request):
    """API endpoint for workspace status (for AJAX polling)"""
    manager = UserContainerManager()
    status = manager.get_container_status(request.user)

    if status:
        return JsonResponse(
            {
                "exists": True,
                "status": status["status"],
                "name": status["name"],
                "id": status["id"][:12],
            }
        )
    else:
        return JsonResponse(
            {
                "exists": False,
                "status": "not_created",
            }
        )


@login_required
def exec_command(request):
    """Execute command in user's workspace container"""
    if request.method == "POST":
        command = request.POST.get("command", "").strip()

        if not command:
            return JsonResponse({"error": "No command provided"}, status=400)

        manager = UserContainerManager()

        try:
            # Parse command into list
            import shlex

            cmd_list = shlex.split(command)

            exit_code, output = manager.exec_command(request.user, cmd_list)

            return JsonResponse(
                {
                    "success": True,
                    "exit_code": exit_code,
                    "output": output,
                }
            )
        except Exception as e:
            return JsonResponse(
                {
                    "success": False,
                    "error": str(e),
                },
                status=500,
            )

    return JsonResponse({"error": "Only POST allowed"}, status=405)


@login_required
def workspace_shell(request, module="writer"):
    """Shell page — renders once. Modules load via AJAX into right pane."""
    from apps.project_app.services.project_utils import get_current_project

    current_project = (
        get_current_project(request) if request.user.is_authenticated else None
    )
    return render(
        request,
        "workspace_app/shell.html",
        {
            "active_module": module,
            "current_project": current_project,
        },
    )


@login_required
def workspace_module_content(request, module):
    """AJAX endpoint — returns module partial HTML for injection into #ws-module-pane."""
    if not request.headers.get("X-Workspace-Shell"):
        from django.http import HttpResponseForbidden

        return HttpResponseForbidden("Direct access not allowed")
    PARTIAL_MAP = {
        "hub": "hub_app/index_partial.html",
        "writer": "writer_app/writer_partial.html",
        "scholar": "scholar_app/scholar_partial.html",
        "console": "console_app/console_partial.html",
        "vis": "vis_app/vis_partial.html",
        "clew": "clew_app/index_partial.html",
    }
    template = PARTIAL_MAP.get(module)
    if not template:
        from django.http import HttpResponseNotFound

        return HttpResponseNotFound(f"Module '{module}' not found")
    from apps.project_app.services.project_utils import get_current_project

    current_project = (
        get_current_project(request) if request.user.is_authenticated else None
    )
    return render(request, template, {"current_project": current_project})


# EOF
