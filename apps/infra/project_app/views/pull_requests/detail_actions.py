#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pull Request Detail - Actions (merge, close, reopen)."""

from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from apps.infra.project_app.models import Project, PullRequest, PullRequestEvent

logger = logging.getLogger(__name__)


@login_required
@require_POST
def pr_merge(request, username, slug, pr_number):
    """
    Merge PR (with merge strategies: merge commit, squash, rebase).

    URL: /<username>/<slug>/pull/<pr_number>/merge/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)
    pr = get_object_or_404(PullRequest, project=project, number=pr_number)

    # Check permissions
    if not project.can_edit(request.user):
        return JsonResponse({"error": "Permission denied"}, status=403)

    # Get merge strategy
    strategy = request.POST.get("strategy", "merge")  # merge, squash, rebase
    commit_message = request.POST.get("commit_message", "")

    # Validate strategy
    if strategy not in ["merge", "squash", "rebase"]:
        return JsonResponse({"error": "Invalid merge strategy"}, status=400)

    # Attempt merge
    success, message = pr.merge(
        request.user, strategy=strategy, commit_message=commit_message
    )

    if success:
        PullRequestEvent.objects.create(
            pull_request=pr,
            event_type="merged",
            actor=request.user,
            metadata={"strategy": strategy},
        )
        return JsonResponse(
            {
                "success": True,
                "message": message,
                "redirect_url": pr.get_absolute_url(),
            }
        )
    else:
        return JsonResponse({"success": False, "error": message}, status=400)


@login_required
@require_POST
def pr_close(request, username, slug, pr_number):
    """
    Close PR without merging.

    URL: /<username>/<slug>/pull/<pr_number>/close/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)
    pr = get_object_or_404(PullRequest, project=project, number=pr_number)

    success, message = pr.close(request.user)

    if success:
        PullRequestEvent.objects.create(
            pull_request=pr,
            event_type="closed",
            actor=request.user,
        )
        return JsonResponse({"success": True, "message": message})
    else:
        return JsonResponse({"success": False, "error": message}, status=400)


@login_required
@require_POST
def pr_reopen(request, username, slug, pr_number):
    """
    Reopen a closed PR.

    URL: /<username>/<slug>/pull/<pr_number>/reopen/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)
    pr = get_object_or_404(PullRequest, project=project, number=pr_number)

    success, message = pr.reopen(request.user)

    if success:
        PullRequestEvent.objects.create(
            pull_request=pr,
            event_type="reopened",
            actor=request.user,
        )
        return JsonResponse({"success": True, "message": message})
    else:
        return JsonResponse({"success": False, "error": message}, status=400)


# EOF
