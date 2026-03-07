#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App submission and staff review API views.

Submission creates a PR on the central ``scitex/apps`` registry.
Staff review actions (approve/reject/request_changes) act through that PR.
"""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from ..models import AppsModule, ModuleSubmission

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def api_submit_for_review(request, module_name):
    """Submit a private module for apps publication review.

    Opens a PR on the central ``scitex/apps`` registry (same pipeline
    as the CLI ``scitex cloud app submit``).
    """
    app_module = get_object_or_404(
        AppsModule, module_name=module_name, author=request.user
    )

    from ..validators import validate_module_for_publication

    errors = validate_module_for_publication(app_module)
    if errors:
        return JsonResponse({"success": False, "errors": errors}, status=400)

    if ModuleSubmission.objects.filter(module=app_module, status="pending").exists():
        return JsonResponse(
            {"success": False, "error": "A submission is already pending review."},
            status=400,
        )

    # Open a PR on the central registry — single pipeline for all paths
    from .api_registry import _fetch_head_commit, _open_registry_pr

    pinned_commit = _fetch_head_commit(request.user.username, app_module.project.slug)

    manifest = {
        "name": app_module.module_name,
        "description": app_module.short_description,
        "category": app_module.category,
        "version": getattr(app_module, "latest_version", "0.1.0") or "0.1.0",
    }
    version = manifest["version"]

    pr_url = _open_registry_pr(
        app_module=app_module,
        manifest=manifest,
        version=version,
        author_username=request.user.username,
        pinned_commit=pinned_commit,
    )

    # Update pinned commit
    app_module.pinned_commit = pinned_commit
    app_module.save(update_fields=["pinned_commit"])

    submission = ModuleSubmission.objects.create(
        module=app_module,
        submitted_by=request.user,
        pr_url=pr_url,
    )
    return JsonResponse(
        {
            "success": True,
            "message": "Submitted for review.",
            "pr_url": pr_url,
            "submission_id": submission.pk,
        }
    )


@login_required
@require_http_methods(["POST"])
def api_review_submission(request, submission_id):
    """Staff reviews a submission by acting through the registry PR.

    - ``approve``  → merges the PR on scitex/apps (webhook auto-activates)
    - ``reject``   → closes the PR with a comment
    - ``request_changes`` → adds a review comment on the PR
    """
    if not request.user.is_staff:
        return JsonResponse({"success": False, "error": "Staff only."}, status=403)

    from django.utils import timezone

    submission = get_object_or_404(ModuleSubmission, id=submission_id)
    if submission.status not in ("pending", "changes_requested"):
        return JsonResponse(
            {"success": False, "error": "Submission already reviewed."}, status=400
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."}, status=400)

    action = data.get("action")
    note = data.get("note", "")
    now = timezone.now()

    from .api_registry import (
        close_registry_pr,
        comment_on_registry_pr,
        merge_registry_pr,
    )

    pr_url = submission.pr_url or ""

    if action == "approve":
        if not pr_url:
            return JsonResponse(
                {"success": False, "error": "No PR URL — cannot merge."},
                status=400,
            )
        # Merge the registry PR — webhook will auto-activate the app
        merge_registry_pr(pr_url)
        # Update locally for immediate feedback (webhook also sets this)
        submission.status = "approved"

    elif action == "reject":
        if pr_url:
            comment = f"Rejected by {request.user.username}"
            if note:
                comment += f": {note}"
            close_registry_pr(pr_url, comment=comment)
        submission.status = "rejected"

    elif action == "request_changes":
        if pr_url and note:
            comment_on_registry_pr(
                pr_url,
                f"**Changes requested** by {request.user.username}:\n\n{note}",
            )
        submission.status = "changes_requested"

    else:
        return JsonResponse(
            {
                "success": False,
                "error": "action must be 'approve', 'reject', or 'request_changes'.",
            },
            status=400,
        )

    submission.reviewer = request.user
    submission.review_note = note
    submission.reviewed_at = now
    submission.save()

    # Sync status back to the linked Project
    _sync_project_status(submission, now, request.user)

    # Notify author
    _notify_author(submission)

    return JsonResponse(
        {
            "success": True,
            "message": f"{action.title()} {submission.module.module_name}.",
        }
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


APPS_ORG = "scitex-apps"


def _activate_approved_app(app_module):
    """Pin commit, fork to apps org, and register into the workspace registry."""
    from ..services.app_loader import load_single_app, pin_commit

    pin_commit(app_module)
    _fork_to_apps_org(app_module)
    load_single_app(app_module)


def _fork_to_apps_org(app_module):
    """Fork the author's source repo to the scitex-apps organisation on approval."""
    if not app_module.project:
        return

    from apps.gitea_app.api_client import GiteaAPIError, GiteaClient

    client = GiteaClient()
    owner = app_module.project.owner.username
    repo = app_module.project.slug

    try:
        client.get_repository(owner=APPS_ORG, repo=repo)
        logger.info("Fork already exists: %s/%s", APPS_ORG, repo)
    except GiteaAPIError:
        try:
            client.fork_repository(owner=owner, repo=repo, organization=APPS_ORG)
            logger.info("Forked %s/%s to %s/%s", owner, repo, APPS_ORG, repo)
        except GiteaAPIError:
            logger.exception("Failed to fork %s/%s to %s", owner, repo, APPS_ORG)
            return

    # Store the registry repo URL on the module
    app_module.registry_repo_url = f"/{APPS_ORG}/{repo}/"
    app_module.save(update_fields=["registry_repo_url"])


def _sync_project_status(submission, now, reviewer):
    """Update the source Project's app_status fields after review."""
    project = getattr(submission.module, "project", None)
    if project is None:
        return
    project.app_status = submission.status
    project.app_reviewed_at = now
    project.app_reviewer = reviewer
    project.save(update_fields=["app_status", "app_reviewed_at", "app_reviewer"])


def _notify_author(submission):
    """Send email notification to the submission author."""
    try:
        from apps.project_app.services.email_service import EmailService

        EmailService.send_app_review_complete(
            user=submission.submitted_by,
            module_name=submission.module.module_name,
            status=submission.status,
            note=submission.review_note,
        )
    except Exception:
        logger.warning(
            "Failed to send review notification for %s",
            submission.module.module_name,
        )


# EOF
