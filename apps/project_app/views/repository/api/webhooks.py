#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gitea webhook handlers for app CI validation."""

from __future__ import annotations

import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.project_app.models import Project
from apps.project_app.services.app_validator import validate_app

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def webhook_push(request, username, slug):
    """Handle Gitea push webhook — auto-validate app on push.

    POST /<username>/<slug>/api/webhook/push/
    Gitea sends this on every push event if configured.
    """
    try:
        project = Project.objects.get(owner__username=username, slug=slug)
    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )

    if not project.is_app:
        return JsonResponse({"success": True, "skipped": True, "reason": "Not an app"})

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    ref = payload.get("ref", "")
    commit_sha = ""
    commits = payload.get("commits", [])
    if commits:
        commit_sha = commits[-1].get("id", "")

    logger.info(
        "[webhook] Push to %s/%s ref=%s sha=%s — running validation",
        username,
        slug,
        ref,
        commit_sha[:8],
    )

    errors = validate_app(project)

    if errors:
        logger.warning(
            "[webhook] Validation failed for %s/%s: %s", username, slug, errors
        )
    else:
        logger.info("[webhook] Validation passed for %s/%s", username, slug)

    return JsonResponse(
        {
            "success": True,
            "validation_passed": len(errors) == 0,
            "errors": errors,
            "commit": commit_sha,
        }
    )


# EOF
