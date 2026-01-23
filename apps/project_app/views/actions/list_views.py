#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workflow listing and detail views."""

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden
from django.db.models import Count, Avg
from django.core.paginator import Paginator
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


def actions_list(request, username, slug):
    """
    List all workflows for a project

    URL: /<username>/<slug>/actions/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)

    # Check permissions
    if not project.can_view(request.user):
        return HttpResponseForbidden("You don't have permission to view this project")

    # Get all workflows for this project
    workflows = (
        Workflow.objects.filter(project=project)
        .annotate(
            total_runs_count=Count("runs"), avg_duration=Avg("runs__duration_seconds")
        )
        .order_by("-updated_at")
    )

    # Get recent workflow runs (last 10)
    recent_runs = (
        WorkflowRun.objects.filter(workflow__project=project)
        .select_related("workflow", "trigger_user")
        .order_by("-created_at")[:10]
    )

    # Calculate statistics
    total_workflows = workflows.count()
    enabled_workflows = workflows.filter(enabled=True).count()
    total_runs = WorkflowRun.objects.filter(workflow__project=project).count()
    successful_runs = WorkflowRun.objects.filter(
        workflow__project=project, conclusion="success"
    ).count()

    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0

    context = {
        "project": project,
        "workflows": workflows,
        "recent_runs": recent_runs,
        "stats": {
            "total_workflows": total_workflows,
            "enabled_workflows": enabled_workflows,
            "total_runs": total_runs,
            "success_rate": round(success_rate, 1),
        },
    }

    return render(request, "project_app/actions/list.html", context)


def workflow_detail(request, username, slug, workflow_id):
    """
    Show workflow definition and runs history

    URL: /<username>/<slug>/actions/workflows/<workflow_id>/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)
    workflow = get_object_or_404(Workflow, id=workflow_id, project=project)

    # Check permissions
    if not project.can_view(request.user):
        return HttpResponseForbidden("You don't have permission to view this project")

    # Get workflow runs with pagination
    runs_list = (
        WorkflowRun.objects.filter(workflow=workflow)
        .select_related("trigger_user")
        .order_by("-run_number")
    )

    paginator = Paginator(runs_list, 20)
    page_number = request.GET.get("page", 1)
    runs = paginator.get_page(page_number)

    # Parse YAML for display
    yaml_data = workflow.parse_yaml()

    # Calculate statistics
    total_runs = runs_list.count()
    successful = runs_list.filter(conclusion="success").count()
    failed = runs_list.filter(conclusion="failure").count()
    cancelled = runs_list.filter(conclusion="cancelled").count()

    # Calculate average duration
    completed_runs = runs_list.filter(
        status="completed", duration_seconds__isnull=False
    )
    avg_duration = completed_runs.aggregate(avg=Avg("duration_seconds"))["avg"] or 0

    context = {
        "project": project,
        "workflow": workflow,
        "runs": runs,
        "yaml_data": yaml_data,
        "stats": {
            "total_runs": total_runs,
            "successful": successful,
            "failed": failed,
            "cancelled": cancelled,
            "success_rate": round(successful / total_runs * 100, 1)
            if total_runs > 0
            else 0,
            "avg_duration": int(avg_duration),
        },
    }

    return render(request, "project_app/workflows/detail.html", context)


def workflow_run_detail(request, username, slug, run_id):
    """
    Show specific run with job logs

    URL: /<username>/<slug>/actions/runs/<run_id>/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)
    run = get_object_or_404(
        WorkflowRun.objects.select_related("workflow", "trigger_user"),
        id=run_id,
        workflow__project=project,
    )

    # Check permissions
    if not project.can_view(request.user):
        return HttpResponseForbidden("You don't have permission to view this project")

    # Get all jobs with their steps
    jobs = (
        WorkflowJob.objects.filter(run=run)
        .prefetch_related("steps")
        .order_by("created_at")
    )

    # Format duration
    duration_text = None
    if run.duration_seconds:
        minutes, seconds = divmod(run.duration_seconds, 60)
        if minutes > 0:
            duration_text = f"{minutes}m {seconds}s"
        else:
            duration_text = f"{seconds}s"

    context = {
        "project": project,
        "workflow": run.workflow,
        "run": run,
        "jobs": jobs,
        "duration_text": duration_text,
    }

    return render(request, "project_app/workflows/run_detail.html", context)


# EOF
