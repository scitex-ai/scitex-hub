"""The SDK project picker's HTTP provider: ``/api/project/scope/``.

GET  -> {"projects": [{id: "owner/slug", name, detail}], "current": last visited id|null}
POST {"id": "owner/slug"} -> stores it as the last visited project (403 if not accessible)
"""

from __future__ import annotations

import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.services.project_scope import (
    HubProjectProvider,
    HubScopedProjectProvider,
    find_accessible_project,
    project_key,
    remember_last_visited,
)


@login_required
@require_http_methods(["GET", "POST"])
def api_project_scope(request):
    # Only trusted server registration enables All; request flags never do.
    scoped = getattr(settings, "SCITEX_PROJECT_PROVIDER", "") == (
        "apps.infra.project_app.services.project_scope.HubScopedProjectProvider"
    )
    provider = HubScopedProjectProvider() if scoped else HubProjectProvider()
    if request.method == "GET":
        entries = provider.list_projects(request)
        body = {
            "projects": [e.as_option() for e in entries],
            "current": provider.last_visited(request),
            "allow_user_scope": scoped,
        }
        if scoped:
            selection = provider.current_scope(request)
            body["current"] = None
            if selection is not None and (
                selection.scope == "user" or selection.id in {e.id for e in entries}
            ):
                body.update(current=selection.id, current_scope=selection.scope)
        return JsonResponse(body)
    try:
        payload = json.loads(request.body or b"{}")
        if not isinstance(payload, dict):
            raise ValueError("selection must be an object")
        if "scope" in payload:
            if not scoped or "id" not in payload:
                raise ValueError("tagged selection requires the server capability")
            from scitex_sdk.ui.project_scope import ProjectSelection

            selection = ProjectSelection(scope=payload["scope"], id=payload["id"])
            provider.remember_scope(request, selection)
            return JsonResponse(
                {"current": selection.id, "current_scope": selection.scope}
            )
        wanted = payload.get("id")
    except ValueError:
        return JsonResponse({"error": "project not accessible"}, status=403)
    project = find_accessible_project(request.user, wanted)
    if project is None:
        return JsonResponse({"error": "project not accessible"}, status=403)
    remember_last_visited(request.user, project)
    return JsonResponse({"current": project_key(project)})
