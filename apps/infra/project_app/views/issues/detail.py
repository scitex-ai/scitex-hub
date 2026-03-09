"""
Issue detail view for SciTeX projects
"""

from django.contrib.auth.models import User
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from apps.infra.project_app.models import Issue
from apps.infra.project_app.utils.project_lookup import get_project_by_owner_slug


def issue_detail(request, username, slug, issue_number):
    """
    Display a single issue with all comments and events
    Similar to GitHub issue detail page

    Supports both user-owned and organization-owned projects.
    """
    project = get_project_by_owner_slug(username, slug)
    issue = get_object_or_404(
        Issue.objects.select_related("author", "milestone", "closed_by"),
        project=project,
        number=issue_number,
    )

    # Check permissions
    if not project.can_view(request.user):
        raise Http404("Issue not found")

    # Get comments
    comments = issue.comments.select_related("author").order_by("created_at")

    # Get events (optional - for timeline)
    events = issue.events.select_related("actor").order_by("created_at")

    # Get labels and milestones for editing
    labels = project.issue_labels.all()
    milestones = project.issue_milestones.filter(state="open")

    # Get potential assignees (project collaborators)
    potential_assignees = project.memberships.select_related("user").values_list(
        "user", flat=True
    )
    assignable_users = User.objects.filter(
        Q(id__in=potential_assignees) | Q(id=project.owner.id)
    ).distinct()

    context = {
        "project": project,
        "issue": issue,
        "comments": comments,
        "events": events,
        "labels": labels,
        "milestones": milestones,
        "assignable_users": assignable_users,
        "can_edit": issue.can_edit(request.user),
        "can_comment": issue.can_comment(request.user),
    }

    return render(request, "project_app/issues/detail.html", context)
