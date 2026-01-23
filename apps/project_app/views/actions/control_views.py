#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workflow control views - trigger and enable/disable."""

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
import logging

from apps.project_app.models import Project
# TODO: Uncomment when workflow models are available
# from apps.project_app.models import (
#     Workflow,
#     WorkflowRun,
#     WorkflowJob,
#     WorkflowStep,
# )

logger = logging.getLogger(__name__)


@login_required
def workflow_trigger(request, username, slug, workflow_id):
    """
    Manually trigger workflow

    URL: /<username>/<slug>/actions/workflows/<workflow_id>/trigger/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)
    workflow = get_object_or_404(Workflow, id=workflow_id, project=project)

    # Check permissions
    if not project.can_edit(request.user):
        return JsonResponse({"error": "Permission denied"}, status=403)

    if request.method == "POST":
        # Check if workflow is enabled
        if not workflow.enabled:
            return JsonResponse({"error": "Workflow is disabled"}, status=400)

        # Get branch (default to current branch)
        branch = request.POST.get("branch", project.current_branch or "main")

        # Create workflow run
        from apps.project_app.tasks.workflow_tasks import execute_workflow_run

        run = WorkflowRun.objects.create(
            workflow=workflow,
            trigger_event="manual",
            trigger_user=request.user,
            trigger_data={
                "branch": branch,
                "triggered_by": request.user.username,
            },
            branch=branch,
            status="queued",
        )

        # Queue workflow execution (Celery task)
        execute_workflow_run.delay(run.id)

        messages.success(request, f"Workflow '{workflow.name}' triggered successfully")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "run_id": run.id,
                    "run_url": run.get_absolute_url(),
                }
            )
        else:
            return redirect(
                "user_projects:workflow_run_detail",
                username=username,
                slug=slug,
                run_id=run.id,
            )

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def workflow_enable_disable(request, username, slug, workflow_id):
    """
    Enable or disable workflow

    URL: /<username>/<slug>/actions/workflows/<workflow_id>/toggle/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)
    workflow = get_object_or_404(Workflow, id=workflow_id, project=project)

    # Check permissions
    if not project.can_edit(request.user):
        return JsonResponse({"error": "Permission denied"}, status=403)

    if request.method == "POST":
        workflow.enabled = not workflow.enabled
        workflow.save()

        status = "enabled" if workflow.enabled else "disabled"
        messages.success(request, f"Workflow '{workflow.name}' {status}")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "enabled": workflow.enabled,
                }
            )
        else:
            return redirect(
                "user_projects:workflow_detail",
                username=username,
                slug=slug,
                workflow_id=workflow.id,
            )

    return JsonResponse({"error": "Method not allowed"}, status=405)


# EOF
