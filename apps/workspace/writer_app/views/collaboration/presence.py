"""Presence heartbeat for the writer collab pane (slice 1, 2026-10-24).

The leaf editor polls these endpoints in hub-mounted mode to show who is
here. Built directly on the WriterPresence model: the CollaborationService
presence methods are unimplemented stubs (start_session/update_presence
raise NotImplementedError; its get_active_users queries manuscript/cursor
fields the model does not have). This module is the narrow working surface
the leaf polls; repairing the service is its own card.
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.models import Project
from ...models.collaboration.session import WriterPresence

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 25
ACTIVE_WINDOW_MINUTES = 2


def _resolve_visible_project(request, ref):
    """Resolve a project ref (int id or 'owner/slug') the user may view.

    Returns None for unknown OR invisible projects alike — a 404 either
    way, so the endpoint is not an existence oracle for private projects.
    """
    project = None
    try:
        if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
            project = Project.objects.select_related("owner").get(pk=int(ref))
        elif isinstance(ref, str) and "/" in ref:
            owner_slug, slug = ref.split("/", 1)
            project = Project.objects.select_related("owner").get(
                owner__username=owner_slug.strip(),
                slug=slug.strip(),
            )
    except (Project.DoesNotExist, ValueError):
        return None
    if project is not None and not project.can_view(request.user):
        return None
    return project


@login_required
@require_http_methods(["POST"])
def heartbeat_api(request):
    """Record the caller's presence in a project.

    POST body: {"project": <id | "owner/slug">, "section": "<optional>"}.
    Upserts (user, project), touches last_seen, forces is_active True.
    """
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"success": False, "error": "invalid JSON"}, status=400)
    project = _resolve_visible_project(request, data.get("project"))
    if project is None:
        return JsonResponse(
            {"success": False, "error": "project not found"}, status=404
        )
    section = str(data.get("section") or "")[:100]
    try:
        WriterPresence.objects.update_or_create(
            user=request.user,
            project=project,
            defaults={"current_section": section, "is_active": True},
        )
    except Exception as e:  # noqa: BLE001 - heartbeat must never 500 the pane
        logger.error("presence heartbeat failed: %s", e, exc_info=True)
        return JsonResponse({"success": False, "error": "unavailable"}, status=503)
    return JsonResponse({"success": True})


@login_required
@require_http_methods(["GET"])
def active_api(request):
    """List users recently seen in a project.

    GET ?project=<id | "owner/slug">. Active = heartbeat within the
    model's window. Never includes the caller-or-not distinction — the
    leaf renders every active user including self.
    """
    project = _resolve_visible_project(request, request.GET.get("project"))
    if project is None:
        return JsonResponse(
            {"success": False, "error": "project not found"}, status=404
        )
    presences = WriterPresence.get_active_users(
        project.id, minutes=ACTIVE_WINDOW_MINUTES
    )
    return JsonResponse(
        {
            "success": True,
            "users": [
                {
                    "username": p.user.username,
                    "section": p.current_section,
                }
                for p in presences
            ],
        }
    )
