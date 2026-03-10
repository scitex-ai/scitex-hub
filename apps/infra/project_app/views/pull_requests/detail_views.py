#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pull Request Detail - Main View."""

from __future__ import annotations

import logging

from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from apps.infra.project_app.models import (
    Project,
    PullRequest,
    PullRequestComment,
    PullRequestCommit,
    PullRequestEvent,
    PullRequestReview,
)

from .detail_utils import get_pr_checks, get_pr_diff, get_pr_timeline

logger = logging.getLogger(__name__)


def pr_detail(request, username, slug, pr_number):
    """
    Show PR detail with diff, commits, conversation.

    URL: /<username>/<slug>/pull/<pr_number>/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)
    pr = get_object_or_404(PullRequest, project=project, number=pr_number)

    # Check permissions
    if not project.can_view(request.user):
        raise Http404("Project not found")

    # Get tab (conversation, commits, files, checks)
    active_tab = request.GET.get("tab", "conversation")

    # Get PR data with related objects
    pr = _get_pr_with_prefetch(project, pr_number)
    if not pr:
        raise Http404("Pull request not found")

    # Get approval status
    approval_status = pr.get_approval_status()

    # Check if user can merge
    can_merge, merge_reason = (
        pr.can_merge(request.user)
        if request.user.is_authenticated
        else (False, "Not authenticated")
    )

    # Get diff if on files tab
    diff_data = None
    changed_files = []
    if active_tab == "files":
        diff_data, changed_files = get_pr_diff(project, pr)

    # Get checks status (if checks are configured)
    checks = []
    if active_tab == "checks":
        checks = get_pr_checks(project, pr)

    # Get timeline (comments + events merged chronologically)
    timeline = get_pr_timeline(pr)

    context = {
        "project": project,
        "pr": pr,
        "active_tab": active_tab,
        "approval_status": approval_status,
        "can_merge": can_merge,
        "merge_reason": merge_reason,
        "can_edit": project.can_edit(request.user),
        "is_author": (
            request.user == pr.author if request.user.is_authenticated else False
        ),
        "diff_data": diff_data,
        "changed_files": changed_files,
        "checks": checks,
        "timeline": timeline,
    }

    return render(request, "project_app/pull_requests/detail.html", context)


def _get_pr_with_prefetch(project, pr_number):
    """Get PR with all related objects prefetched."""
    return (
        PullRequest.objects.filter(project=project, number=pr_number)
        .select_related("author", "merged_by")
        .prefetch_related(
            "reviewers",
            "assignees",
            Prefetch(
                "comments",
                queryset=PullRequestComment.objects.select_related("author"),
            ),
            Prefetch(
                "reviews",
                queryset=PullRequestReview.objects.select_related("reviewer"),
            ),
            Prefetch("commits", queryset=PullRequestCommit.objects.all()),
            Prefetch(
                "events",
                queryset=PullRequestEvent.objects.select_related("actor"),
            ),
        )
        .first()
    )


# EOF
