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


def workspace_shell(request, module="chat"):
    """Shell page — renders once. Modules load via AJAX into right pane.

    Unauthenticated users are redirected to the landing page (not login)
    to avoid a confusing 404 or login-wall when visiting /workspace/ directly.
    """
    if not request.user.is_authenticated:
        return redirect("public_app:landing")

    # The legacy 3-pane robot-icon chat shell is RETIRED: the chat module now
    # renders as the snake-logo pane in the unified workspace layout. Redirect
    # any direct hit on the chat shell (/apps/workspace/chat/, and the bare
    # /apps/workspace/ which defaults to module="chat") to the canonical /chat/
    # route so the robot chat can never be reached again. Other modules
    # (console, editor) keep the shell — they are separate lanes.
    if module == "chat":
        return redirect("pane-chat")

    from apps.infra.project_app.services.project_utils import get_current_project

    current_project = get_current_project(request)
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

    # Dev-installed apps: resolve template from user's project dir
    if module.startswith("dev__"):
        return _serve_dev_module(request, module)

    from .registry import get_module

    mod_config = get_module(module)
    if not mod_config or not mod_config.partial_template:
        from django.http import HttpResponseNotFound

        return HttpResponseNotFound(f"Module '{module}' not found")

    from apps.infra.project_app.services.project_utils import get_current_project

    current_project = (
        get_current_project(request) if request.user.is_authenticated else None
    )

    ctx = mod_config.build_context(request, current_project)
    return render(request, mod_config.partial_template, ctx)


def _serve_dev_module(request, module):
    """Serve a dev-installed app's partial template with sandboxed context."""
    from django.http import HttpResponse, HttpResponseNotFound
    from django.template import engines

    from apps.workspace.apps_app.services.dev_app_loader import resolve_dev_template

    template_path = resolve_dev_template(module)
    if not template_path:
        return HttpResponseNotFound(f"Dev module '{module}' template not found")

    # Parse owner/repo from dev__ prefix
    parts = module.split("__", 2)
    if len(parts) != 3:
        from django.http import HttpResponseServerError

        return HttpResponseServerError(f"Invalid dev module name: {module}")

    owner, repo = parts[1], parts[2]

    # Get dev_install record
    dev_install = None
    try:
        from apps.workspace.apps_app.models import DevInstallation

        dev_install = DevInstallation.objects.filter(
            source_owner=owner,
            source_repo=repo,
            user=request.user,
            is_enabled=True,
        ).first()
    except Exception:
        pass

    # Build context: run views.py context builder inside Apptainer (if available)
    context = {"request": request}
    if dev_install is not None:
        from apps.infra.project_app.services.project_utils import get_current_project
        from apps.workspace.apps_app.services.dev_app_runner import run_dev_context

        current_project = None
        try:
            current_project = get_current_project(request)
        except Exception:
            pass

        extra_ctx = run_dev_context(
            dev_install=dev_install,
            username=request.user.username,
            project_id=current_project.id if current_project else None,
            project_slug=current_project.slug if current_project else "",
            get_params=dict(request.GET),
        )
        context.update(extra_ctx)
        context["current_project"] = current_project

    try:
        raw = template_path.read_text(encoding="utf-8")
        engine = engines["django"]
        tpl = engine.from_string(raw)
        html = tpl.render(context, request)
        return HttpResponse(html)
    except Exception as e:
        from django.http import HttpResponseServerError

        return HttpResponseServerError(f"Dev module '{module}' render error: {e}")


# EOF
