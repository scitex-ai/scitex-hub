#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App submission and staff review API views.

Reverse-fork model: PRs target ``scitex-apps/<repo>`` directly.
Staff review actions (approve/reject/request_changes) act through those PRs.
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

    Opens a cross-repo PR: ``user/<app>`` -> ``scitex-apps/<app>``.
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

    from .api_registry import _fetch_head_commit, _submit_app_pr

    pinned_commit = _fetch_head_commit(request.user.username, app_module.project.slug)

    version = getattr(app_module, "latest_version", "0.1.0") or "0.1.0"

    # Update pinned commit
    app_module.pinned_commit = pinned_commit
    app_module.save(update_fields=["pinned_commit"])

    pr_url = _submit_app_pr(
        app_module=app_module,
        version=version,
    )

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
    """Staff reviews a submission by acting through the app PR.

    - ``approve``  -> merges the PR on scitex-apps/<repo> (webhook auto-activates)
    - ``reject``   -> closes the PR with a comment
    - ``request_changes`` -> adds a review comment on the PR
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

    from .api_registry import close_app_pr, comment_on_app_pr, merge_app_pr

    pr_url = submission.pr_url or ""
    app_repo = submission.module.project.slug if submission.module.project else ""

    if action == "approve":
        if not pr_url:
            return JsonResponse(
                {"success": False, "error": "No PR URL — cannot merge."},
                status=400,
            )
        merge_app_pr(pr_url, app_repo)
        submission.status = "approved"

    elif action == "reject":
        if pr_url:
            comment = f"Rejected by {request.user.username}"
            if note:
                comment += f": {note}"
            close_app_pr(pr_url, app_repo, comment=comment)
        submission.status = "rejected"

    elif action == "request_changes":
        if pr_url and note:
            comment_on_app_pr(
                pr_url,
                app_repo,
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

    _sync_project_status(submission, now, request.user)
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


def _activate_approved_app(app_module):
    """Pin commit, pip-install from Gitea, register into workspace registry.

    F0+F1 (operator-A pick, lead msg 34a4b271):

      1. ``pin_commit`` — record the latest scitex-apps/<repo> SHA so
         subsequent activations are reproducible (existing behaviour).
      2. ``pip_install_user_app`` — pull the package tarball from the
         Gitea mirror at the pinned commit + install with
         ``--no-deps --target=<hub-managed-dir>`` so the user-app's
         module becomes importable by the Django process WITHOUT
         polluting the hub venv. NEW (F0).
      3. ``load_single_app`` — register the ModuleConfig (existing
         partial-template surface) AND populate the URL-patterns
         cache from the ``scitex_hub.apps`` entry-point (F1, the
         ``/apps/u/<module_name>/`` dispatcher consumes this cache).

    Rollback contract: any failure in step 2 raises ``RuntimeError``
    + the activation surface for the AppsModule stays unchanged
    (caller's outer ``api_registry_webhook`` returns 500; no half-
    state where the module is "approved" but not importable).
    """
    from ..services._user_app_install import pip_install_user_app
    from ..services.app_loader import load_single_app, pin_commit

    pin_commit(app_module)
    pip_install_user_app(app_module)
    load_single_app(app_module)


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
        from apps.infra.project_app.services.email_service import EmailService

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
