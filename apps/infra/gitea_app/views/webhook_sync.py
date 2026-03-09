#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gitea → Django sync webhook handler.

Handles org-level and repo-level Gitea webhook events and reflects them
into Django Organization / OrganizationMembership models.

Register this endpoint in Gitea as an org-level webhook:
  URL: /api/gitea/webhook/sync/
  Content-Type: application/json
  Events: Members, Collaborators (all push events if needed)
"""

from __future__ import annotations

import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def gitea_sync_webhook(request):
    """Org/repo-level Gitea webhook — sync members and collaborators to Django.

    Gitea event header: X-Gitea-Event
    Supported events:
      - member        (organization member added/removed)
      - pull_request  (ignored here — handled by api_registry_webhook)
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    event = request.headers.get("X-Gitea-Event", "")

    if event == "member":
        return _handle_member_event(payload)

    # Unknown / unhandled event — acknowledge silently
    return JsonResponse({"ok": True, "skipped": f"unhandled event: {event}"})


def _handle_member_event(payload: dict) -> JsonResponse:
    """Handle Gitea 'member' webhook event (org member added/removed)."""
    from apps.infra.gitea_app.services.org_sync import (
        sync_org_member_added,
        sync_org_member_removed,
    )

    action = payload.get("action")  # "added" or "removed"
    org_data = payload.get("organization", {})
    member_data = payload.get("member", {})

    org_name = org_data.get("login") or org_data.get("username") or org_data.get("name")
    username = member_data.get("login") or member_data.get("username")

    if not org_name or not username:
        return JsonResponse(
            {"ok": False, "error": "Missing org or member info"}, status=400
        )

    if action == "added":
        sync_org_member_added(org_name, username)
        return JsonResponse(
            {"ok": True, "action": "member_added", "org": org_name, "user": username}
        )

    if action == "removed":
        sync_org_member_removed(org_name, username)
        return JsonResponse(
            {"ok": True, "action": "member_removed", "org": org_name, "user": username}
        )

    return JsonResponse({"ok": True, "skipped": f"unknown member action: {action}"})


# EOF
