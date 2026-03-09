"""
Issue form views (create, edit, comment) for SciTeX projects
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.infra.project_app.models import (
    Issue,
    IssueAssignment,
    IssueComment,
    IssueEvent,
    IssueLabel,
    IssueMilestone,
    IssueTemplate,
)
from apps.infra.project_app.utils.project_lookup import get_project_by_owner_slug


@login_required
def issue_create(request, username, slug):
    """
    Create a new issue

    Supports both user-owned and organization-owned projects.
    """
    project = get_project_by_owner_slug(username, slug)

    # Check permissions (can view = can create issues)
    if not project.can_view(request.user):
        raise Http404("Project not found")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        label_ids = request.POST.getlist("labels")
        milestone_id = request.POST.get("milestone")
        assignee_ids = request.POST.getlist("assignees")

        # Validation
        if not title:
            messages.error(request, "Issue title is required")
            return redirect("project_app:issue_create", username=username, slug=slug)

        # Create issue
        issue = Issue.objects.create(
            project=project,
            title=title,
            description=description,
            author=request.user,
        )

        # Add labels
        if label_ids:
            labels = IssueLabel.objects.filter(id__in=label_ids, project=project)
            issue.labels.set(labels)

        # Add milestone
        if milestone_id:
            try:
                milestone = IssueMilestone.objects.get(id=milestone_id, project=project)
                issue.milestone = milestone
                issue.save()
            except IssueMilestone.DoesNotExist:
                pass

        # Add assignees
        if assignee_ids and project.can_edit(request.user):
            for user_id in assignee_ids:
                try:
                    user = User.objects.get(id=user_id)
                    IssueAssignment.objects.create(
                        issue=issue, user=user, assigned_by=request.user
                    )
                except User.DoesNotExist:
                    pass

        # Create event
        IssueEvent.objects.create(issue=issue, event_type="created", actor=request.user)

        messages.success(request, f"Issue #{issue.number} created successfully")
        return redirect(issue.get_absolute_url())

    # GET request - show form
    labels = project.issue_labels.all()
    milestones = project.issue_milestones.filter(state="open")
    templates = project.issue_templates.filter(is_active=True)

    # Get potential assignees
    potential_assignees = project.memberships.select_related("user").values_list(
        "user", flat=True
    )
    assignable_users = User.objects.filter(
        Q(id__in=potential_assignees) | Q(id=project.owner.id)
    ).distinct()

    # Check if template was selected (from template selector)
    template_id = request.GET.get("template")
    selected_template = None
    prefilled_title = ""
    prefilled_description = ""
    preselected_labels = []

    if template_id:
        try:
            selected_template = templates.get(id=template_id)
            prefilled_title = selected_template.title_prefix
            prefilled_description = selected_template.body_template
            preselected_labels = list(
                selected_template.labels.values_list("id", flat=True)
            )
        except IssueTemplate.DoesNotExist:
            pass

    context = {
        "project": project,
        "labels": labels,
        "milestones": milestones,
        "assignable_users": assignable_users,
        "templates": templates,
        "selected_template": selected_template,
        "prefilled_title": prefilled_title,
        "prefilled_description": prefilled_description,
        "preselected_labels": preselected_labels,
    }

    return render(request, "project_app/issues/form.html", context)


@login_required
def issue_edit(request, username, slug, issue_number):
    """
    Edit an existing issue

    Supports both user-owned and organization-owned projects.
    """
    project = get_project_by_owner_slug(username, slug)
    issue = get_object_or_404(Issue, project=project, number=issue_number)

    # Check permissions
    if not issue.can_edit(request.user):
        messages.error(request, "You do not have permission to edit this issue")
        return redirect(issue.get_absolute_url())

    if request.method == "POST":
        old_title = issue.title
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()

        # Validation
        if not title:
            messages.error(request, "Issue title is required")
            return redirect(
                "project_app:issue_edit",
                username=username,
                slug=slug,
                issue_number=issue_number,
            )

        # Update issue
        issue.title = title
        issue.description = description
        issue.save()

        # Track rename event
        if old_title != title:
            IssueEvent.objects.create(
                issue=issue,
                event_type="renamed",
                actor=request.user,
                metadata={"old_title": old_title, "new_title": title},
            )

        messages.success(request, f"Issue #{issue.number} updated successfully")
        return redirect(issue.get_absolute_url())

    # GET request - show form
    context = {
        "project": project,
        "issue": issue,
        "edit_mode": True,
    }

    return render(request, "project_app/issues/form.html", context)


@login_required
def issue_comment_create(request, username, slug, issue_number):
    """
    Add a comment to an issue

    Supports both user-owned and organization-owned projects.
    """
    project = get_project_by_owner_slug(username, slug)
    issue = get_object_or_404(Issue, project=project, number=issue_number)

    # Check permissions
    if not issue.can_comment(request.user):
        messages.error(request, "You do not have permission to comment on this issue")
        return redirect(issue.get_absolute_url())

    if request.method == "POST":
        content = request.POST.get("content", "").strip()

        if not content:
            messages.error(request, "Comment content is required")
            return redirect(issue.get_absolute_url())

        # Create comment
        comment = IssueComment.objects.create(
            issue=issue, author=request.user, content=content
        )

        messages.success(request, "Comment added successfully")
        return redirect(issue.get_absolute_url() + f"#comment-{comment.id}")

    return redirect(issue.get_absolute_url())
