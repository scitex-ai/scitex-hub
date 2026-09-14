"""The SDK project picker's HTTP provider: ``/api/project/scope/``.

GET  -> {"projects": [{id: "owner/slug", name, detail}], "current": last visited id|null}
POST {"id": "owner/slug"} -> stores it as the last visited project (403 if not accessible)
"""

from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.services.project_scope import (
    HubProjectProvider,
    find_accessible_project,
    project_key,
    remember_last_visited,
)


@login_required
@require_http_methods(["GET", "POST"])
def api_project_scope(request):
    provider = HubProjectProvider()
    if request.method == "GET":
        return JsonResponse(
            {
                "projects": [e.as_option() for e in provider.list_projects(request)],
                "current": provider.last_visited(request),
            }
        )
    try:
        wanted = json.loads(request.body or b"{}").get("id")
    except (ValueError, AttributeError):
        wanted = None
    project = find_accessible_project(request.user, wanted)
    if project is None:
        return JsonResponse({"error": "project not accessible"}, status=403)
    remember_last_visited(request.user, project)
    return JsonResponse({"current": project_key(project)})
