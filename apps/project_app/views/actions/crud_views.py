#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workflow create, edit, and delete views."""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
import yaml
import logging

from apps.project_app.models import Project
# TODO: Uncomment when workflow models are available
# from apps.project_app.models import (
#     Workflow,
#     WorkflowRun,
#     WorkflowJob,
#     WorkflowStep,
# )
from .helpers import (
    get_workflow_template,
    get_available_templates,
    save_workflow_to_filesystem,
    delete_workflow_from_filesystem,
)

logger = logging.getLogger(__name__)


@login_required
def workflow_create(request, username, slug):
    """
    Create workflow from template or custom YAML

    URL: /<username>/<slug>/actions/new/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)

    # Check permissions
    if not project.can_edit(request.user):
        return HttpResponseForbidden("You don't have permission to edit this project")

    if request.method == "POST":
        workflow_name = request.POST.get("name")
        yaml_content = request.POST.get("yaml_content")
        template = request.POST.get("template")

        # If template selected, load template YAML
        if template:
            yaml_content = get_workflow_template(template)

        # Validate YAML
        try:
            yaml_data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            messages.error(request, f"Invalid YAML: {str(e)}")
            return render(
                request,
                "project_app/workflows/editor.html",
                {
                    "project": project,
                    "yaml_content": yaml_content,
                    "workflow_name": workflow_name,
                },
            )

        # Extract trigger events from YAML
        trigger_events = []
        if "on" in yaml_data:
            on_config = yaml_data["on"]
            if isinstance(on_config, str):
                trigger_events.append(on_config)
            elif isinstance(on_config, list):
                trigger_events.extend(on_config)
            elif isinstance(on_config, dict):
                trigger_events.extend(on_config.keys())

        # Create workflow
        workflow = Workflow.objects.create(
            project=project,
            name=workflow_name,
            file_path=f".scitex/workflows/{workflow_name.lower().replace(' ', '_')}.yml",
            yaml_content=yaml_content,
            trigger_events=trigger_events,
            created_by=request.user,
        )

        # Save to filesystem
        save_workflow_to_filesystem(workflow)

        messages.success(request, f"Workflow '{workflow_name}' created successfully")
        return redirect(
            "user_projects:workflow_detail",
            username=username,
            slug=slug,
            workflow_id=workflow.id,
        )

    # GET request - show form
    templates = get_available_templates()

    context = {
        "project": project,
        "templates": templates,
    }

    return render(request, "project_app/workflows/editor.html", context)


@login_required
def workflow_edit(request, username, slug, workflow_id):
    """
    Edit existing workflow

    URL: /<username>/<slug>/actions/workflows/<workflow_id>/edit/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)
    workflow = get_object_or_404(Workflow, id=workflow_id, project=project)

    # Check permissions
    if not project.can_edit(request.user):
        return HttpResponseForbidden("You don't have permission to edit this project")

    if request.method == "POST":
        workflow_name = request.POST.get("name")
        yaml_content = request.POST.get("yaml_content")

        # Validate YAML
        try:
            yaml_data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            messages.error(request, f"Invalid YAML: {str(e)}")
            return render(
                request,
                "project_app/workflows/editor.html",
                {
                    "project": project,
                    "workflow": workflow,
                    "yaml_content": yaml_content,
                    "workflow_name": workflow_name,
                    "edit_mode": True,
                },
            )

        # Extract trigger events
        trigger_events = []
        if "on" in yaml_data:
            on_config = yaml_data["on"]
            if isinstance(on_config, str):
                trigger_events.append(on_config)
            elif isinstance(on_config, list):
                trigger_events.extend(on_config)
            elif isinstance(on_config, dict):
                trigger_events.extend(on_config.keys())

        # Update workflow
        workflow.name = workflow_name
        workflow.yaml_content = yaml_content
        workflow.trigger_events = trigger_events
        workflow.save()

        # Update filesystem
        save_workflow_to_filesystem(workflow)

        messages.success(request, f"Workflow '{workflow_name}' updated successfully")
        return redirect(
            "user_projects:workflow_detail",
            username=username,
            slug=slug,
            workflow_id=workflow.id,
        )

    # GET request - show form with existing data
    context = {
        "project": project,
        "workflow": workflow,
        "yaml_content": workflow.yaml_content,
        "workflow_name": workflow.name,
        "edit_mode": True,
    }

    return render(request, "project_app/workflows/editor.html", context)


@login_required
def workflow_delete(request, username, slug, workflow_id):
    """
    Delete workflow

    URL: /<username>/<slug>/actions/workflows/<workflow_id>/delete/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)
    workflow = get_object_or_404(Workflow, id=workflow_id, project=project)

    # Check permissions
    if not project.can_edit(request.user):
        return HttpResponseForbidden("You don't have permission to edit this project")

    if request.method == "POST":
        workflow_name = workflow.name
        workflow.delete()

        # Delete from filesystem
        delete_workflow_from_filesystem(project, workflow)

        messages.success(request, f"Workflow '{workflow_name}' deleted successfully")
        return redirect("user_projects:actions_list", username=username, slug=slug)

    context = {
        "project": project,
        "workflow": workflow,
    }

    return render(request, "project_app/workflows/delete_confirm.html", context)


# EOF
