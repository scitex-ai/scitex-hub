#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Issue label and milestone API endpoints."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from ....models import IssueEvent, IssueLabel, IssueMilestone
from .utils import (
    error_response,
    get_project_and_issue,
    parse_json_or_post,
    success_response,
)


@require_POST
@login_required
def api_issue_label(request, username, slug, issue_number):
    """
    API: Add/remove a label to/from an issue.

    POST /<username>/<slug>/api/issues/<issue_number>/label/
    Body: { "label_id": 123, "action": "add" | "remove" }
    """
    project, issue = get_project_and_issue(username, slug, issue_number)

    # Check permissions
    if not project.can_edit(request.user):
        return error_response("You do not have permission to modify labels", status=403)

    data = parse_json_or_post(request)
    label_id = data.get("label_id")
    action = data.get("action", "add")

    if not label_id:
        return error_response("Label ID is required")

    try:
        label = IssueLabel.objects.get(id=label_id, project=project)
    except IssueLabel.DoesNotExist:
        return error_response("Label not found", status=404)

    if action == "add":
        issue.labels.add(label)
        IssueEvent.objects.create(
            issue=issue,
            event_type="labeled",
            actor=request.user,
            metadata={"label": label.name, "color": label.color},
        )
        message = f'Label "{label.name}" added successfully'

    elif action == "remove":
        issue.labels.remove(label)
        IssueEvent.objects.create(
            issue=issue,
            event_type="unlabeled",
            actor=request.user,
            metadata={"label": label.name, "color": label.color},
        )
        message = f'Label "{label.name}" removed successfully'

    else:
        return error_response('Invalid action. Use "add" or "remove"')

    return success_response(
        message,
        labels=[
            {"id": label.id, "name": label.name, "color": label.color}
            for label in issue.labels.all()
        ],
    )


@require_POST
@login_required
def api_issue_milestone(request, username, slug, issue_number):
    """
    API: Set or remove milestone for an issue.

    POST /<username>/<slug>/api/issues/<issue_number>/milestone/
    Body: { "milestone_id": 123 } or { "milestone_id": null }
    """
    project, issue = get_project_and_issue(username, slug, issue_number)

    # Check permissions
    if not project.can_edit(request.user):
        return error_response(
            "You do not have permission to modify milestones", status=403
        )

    data = parse_json_or_post(request)
    milestone_id = data.get("milestone_id")

    if milestone_id:
        # Set milestone
        try:
            milestone = IssueMilestone.objects.get(id=milestone_id, project=project)
            issue.milestone = milestone
            issue.save()

            IssueEvent.objects.create(
                issue=issue,
                event_type="milestoned",
                actor=request.user,
                metadata={"milestone": milestone.title},
            )
            message = f'Milestone "{milestone.title}" set successfully'
        except IssueMilestone.DoesNotExist:
            return error_response("Milestone not found", status=404)
    else:
        # Remove milestone
        old_milestone = issue.milestone
        if old_milestone:
            issue.milestone = None
            issue.save()

            IssueEvent.objects.create(
                issue=issue,
                event_type="demilestoned",
                actor=request.user,
                metadata={"milestone": old_milestone.title},
            )
            message = "Milestone removed successfully"
        else:
            message = "Issue has no milestone"

    return JsonResponse(
        {
            "success": True,
            "message": message,
            "milestone": {"id": issue.milestone.id, "title": issue.milestone.title}
            if issue.milestone
            else None,
        }
    )


# EOF
