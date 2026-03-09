#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Issue assignment API endpoints."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST

from ....models import IssueAssignment, IssueEvent
from .utils import (
    error_response,
    get_project_and_issue,
    parse_json_or_post,
    success_response,
)


@require_POST
@login_required
def api_issue_assign(request, username, slug, issue_number):
    """
    API: Assign/unassign a user to/from an issue.

    POST /<username>/<slug>/api/issues/<issue_number>/assign/
    Body: { "user_id": 123, "action": "add" | "remove" }
    """
    project, issue = get_project_and_issue(username, slug, issue_number)

    # Check permissions
    if not project.can_edit(request.user):
        return error_response("You do not have permission to assign users", status=403)

    data = parse_json_or_post(request)
    user_id = data.get("user_id")
    action = data.get("action", "add")

    if not user_id:
        return error_response("User ID is required")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return error_response("User not found", status=404)

    if action == "add":
        assignment, created = IssueAssignment.objects.get_or_create(
            issue=issue, user=user, defaults={"assigned_by": request.user}
        )

        if created:
            IssueEvent.objects.create(
                issue=issue,
                event_type="assigned",
                actor=request.user,
                metadata={"assignee": user.username},
            )
            message = f"{user.username} assigned successfully"
        else:
            message = f"{user.username} is already assigned"

    elif action == "remove":
        deleted_count, _ = IssueAssignment.objects.filter(
            issue=issue, user=user
        ).delete()

        if deleted_count > 0:
            IssueEvent.objects.create(
                issue=issue,
                event_type="unassigned",
                actor=request.user,
                metadata={"assignee": user.username},
            )
            message = f"{user.username} unassigned successfully"
        else:
            message = f"{user.username} was not assigned"

    else:
        return error_response('Invalid action. Use "add" or "remove"')

    return success_response(
        message,
        assignees=[{"id": a.id, "username": a.username} for a in issue.assignees.all()],
    )


# EOF
