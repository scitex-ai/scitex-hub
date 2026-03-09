#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Issue comment API endpoints."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from ....models import IssueComment
from .utils import error_response, get_project_and_issue, success_response


@require_POST
@login_required
def api_issue_comment(request, username, slug, issue_number):
    """
    API: Add a comment to an issue.

    POST /<username>/<slug>/api/issues/<issue_number>/comment/
    """
    _, issue = get_project_and_issue(username, slug, issue_number)

    # Check permissions
    if not issue.can_comment(request.user):
        return error_response(
            "You do not have permission to comment on this issue", status=403
        )

    content = request.POST.get("content", "").strip()
    if not content:
        return error_response("Comment content is required")

    # Create comment
    comment = IssueComment.objects.create(
        issue=issue, author=request.user, content=content
    )

    return success_response(
        "Comment added successfully",
        comment={
            "id": comment.id,
            "author": comment.author.username,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
        },
    )


# EOF
