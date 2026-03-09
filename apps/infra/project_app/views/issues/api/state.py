#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Issue state management API endpoints (close, reopen)."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from ....models import IssueEvent
from .utils import error_response, get_project_and_issue, success_response


@require_POST
@login_required
def api_issue_close(request, username, slug, issue_number):
    """
    API: Close an issue.

    POST /<username>/<slug>/api/issues/<issue_number>/close/
    """
    _, issue = get_project_and_issue(username, slug, issue_number)

    # Check permissions
    if not issue.can_edit(request.user):
        return error_response(
            "You do not have permission to close this issue", status=403
        )

    if issue.state == "closed":
        return error_response("Issue is already closed")

    # Close issue
    issue.close(request.user)

    # Create event
    IssueEvent.objects.create(issue=issue, event_type="closed", actor=request.user)

    return success_response(
        "Issue closed successfully",
        issue={
            "number": issue.number,
            "state": issue.state,
            "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
        },
    )


@require_POST
@login_required
def api_issue_reopen(request, username, slug, issue_number):
    """
    API: Reopen a closed issue.

    POST /<username>/<slug>/api/issues/<issue_number>/reopen/
    """
    _, issue = get_project_and_issue(username, slug, issue_number)

    # Check permissions
    if not issue.can_edit(request.user):
        return error_response(
            "You do not have permission to reopen this issue", status=403
        )

    if issue.state == "open":
        return error_response("Issue is already open")

    # Reopen issue
    issue.reopen()

    # Create event
    IssueEvent.objects.create(issue=issue, event_type="reopened", actor=request.user)

    return success_response(
        "Issue reopened successfully",
        issue={
            "number": issue.number,
            "state": issue.state,
        },
    )


# EOF
