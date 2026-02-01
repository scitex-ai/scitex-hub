"""
Issue label and milestone management views for SciTeX projects
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import redirect, render

from apps.project_app.models import (
    IssueLabel,
    IssueMilestone,
)
from apps.project_app.utils.project_lookup import get_project_by_owner_slug


@login_required
def issue_label_manage(request, username, slug):
    """
    Manage issue labels for a project

    Supports both user-owned and organization-owned projects.
    """
    project = get_project_by_owner_slug(username, slug)

    # Check permissions
    if not project.can_edit(request.user):
        raise Http404("Project not found")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create":
            name = request.POST.get("name", "").strip()
            color = request.POST.get("color", "#0366d6")
            description = request.POST.get("description", "").strip()

            if not name:
                messages.error(request, "Label name is required")
            else:
                # Check if label already exists
                if IssueLabel.objects.filter(project=project, name=name).exists():
                    messages.error(request, f'Label "{name}" already exists')
                else:
                    IssueLabel.objects.create(
                        project=project, name=name, color=color, description=description
                    )
                    messages.success(request, f'Label "{name}" created successfully')

        elif action == "edit":
            label_id = request.POST.get("label_id")
            name = request.POST.get("name", "").strip()
            color = request.POST.get("color", "#0366d6")
            description = request.POST.get("description", "").strip()

            try:
                label = IssueLabel.objects.get(id=label_id, project=project)
                label.name = name
                label.color = color
                label.description = description
                label.save()
                messages.success(request, f'Label "{name}" updated successfully')
            except IssueLabel.DoesNotExist:
                messages.error(request, "Label not found")

        elif action == "delete":
            label_id = request.POST.get("label_id")
            try:
                label = IssueLabel.objects.get(id=label_id, project=project)
                label.delete()
                messages.success(request, "Label deleted successfully")
            except IssueLabel.DoesNotExist:
                messages.error(request, "Label not found")

        return redirect(
            "user_projects:issue_label_manage", username=username, slug=slug
        )

    # GET request
    labels = project.issue_labels.annotate(issue_count=Count("issues")).order_by("name")

    context = {
        "project": project,
        "labels": labels,
    }

    return render(request, "project_app/issues/label_manage.html", context)


@login_required
def issue_milestone_manage(request, username, slug):
    """
    Manage issue milestones for a project

    Supports both user-owned and organization-owned projects.
    """
    project = get_project_by_owner_slug(username, slug)

    # Check permissions
    if not project.can_edit(request.user):
        raise Http404("Project not found")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create":
            title = request.POST.get("title", "").strip()
            description = request.POST.get("description", "").strip()
            due_date = request.POST.get("due_date")

            if not title:
                messages.error(request, "Milestone title is required")
            else:
                # Check if milestone already exists
                if IssueMilestone.objects.filter(project=project, title=title).exists():
                    messages.error(request, f'Milestone "{title}" already exists')
                else:
                    milestone = IssueMilestone.objects.create(
                        project=project, title=title, description=description
                    )
                    if due_date:
                        from django.utils.dateparse import parse_datetime

                        milestone.due_date = parse_datetime(due_date)
                        milestone.save()
                    messages.success(
                        request, f'Milestone "{title}" created successfully'
                    )

        elif action == "edit":
            milestone_id = request.POST.get("milestone_id")
            title = request.POST.get("title", "").strip()
            description = request.POST.get("description", "").strip()
            due_date = request.POST.get("due_date")

            try:
                milestone = IssueMilestone.objects.get(id=milestone_id, project=project)
                milestone.title = title
                milestone.description = description
                if due_date:
                    from django.utils.dateparse import parse_datetime

                    milestone.due_date = parse_datetime(due_date)
                else:
                    milestone.due_date = None
                milestone.save()
                messages.success(request, f'Milestone "{title}" updated successfully')
            except IssueMilestone.DoesNotExist:
                messages.error(request, "Milestone not found")

        elif action == "close":
            milestone_id = request.POST.get("milestone_id")
            try:
                milestone = IssueMilestone.objects.get(id=milestone_id, project=project)
                milestone.close()
                messages.success(request, f'Milestone "{milestone.title}" closed')
            except IssueMilestone.DoesNotExist:
                messages.error(request, "Milestone not found")

        elif action == "reopen":
            milestone_id = request.POST.get("milestone_id")
            try:
                milestone = IssueMilestone.objects.get(id=milestone_id, project=project)
                milestone.reopen()
                messages.success(request, f'Milestone "{milestone.title}" reopened')
            except IssueMilestone.DoesNotExist:
                messages.error(request, "Milestone not found")

        elif action == "delete":
            milestone_id = request.POST.get("milestone_id")
            try:
                milestone = IssueMilestone.objects.get(id=milestone_id, project=project)
                milestone.delete()
                messages.success(request, "Milestone deleted successfully")
            except IssueMilestone.DoesNotExist:
                messages.error(request, "Milestone not found")

        return redirect(
            "user_projects:issue_milestone_manage", username=username, slug=slug
        )

    # GET request
    milestones = project.issue_milestones.annotate(
        issue_count=Count("issues")
    ).order_by("-created_at")

    # Add progress to each milestone
    for milestone in milestones:
        closed, total, percentage = milestone.get_progress()
        milestone.progress_closed = closed
        milestone.progress_total = total
        milestone.progress_percentage = percentage

    context = {
        "project": project,
        "milestones": milestones,
    }

    return render(request, "project_app/issues/milestone_manage.html", context)
