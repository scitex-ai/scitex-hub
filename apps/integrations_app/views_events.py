#!/usr/bin/env python3
# Timestamp: 2026-02-14
# File: apps/integrations_app/views_events.py

"""Event API endpoints — thin Django wrapper over scitex.events schema."""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.accounts_app.auth import authenticate_api_key

from .models import Event


@csrf_exempt
@require_http_methods(["POST"])
def receive_event(request):
    """Receive an event from CLI/HPC/CI.

    POST /api/events/
    Headers: Authorization: Bearer scitex_xxxx...
    Body: {"type": "test_complete", "project": "figrecipe",
           "status": "success", "payload": {...}, "source": "hpc"}
    """
    api_key = authenticate_api_key(request)
    if api_key is None:
        return JsonResponse({"error": "Invalid or missing API key"}, status=401)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    event_type = data.get("type", "")
    if not event_type:
        return JsonResponse({"error": "Missing required field: type"}, status=400)

    event = Event.objects.create(
        user=api_key.user,
        type=event_type,
        project=data.get("project", ""),
        status=data.get("status", "unknown"),
        payload=data.get("payload", {}),
        source=data.get("source", "local"),
    )

    return JsonResponse({"id": event.id, "received": True}, status=201)


@csrf_exempt
@require_http_methods(["GET"])
def list_events(request):
    """Query recent events for the authenticated user.

    GET /api/events/?type=test_complete&project=figrecipe&limit=20
    Headers: Authorization: Bearer scitex_xxxx...
    """
    api_key = authenticate_api_key(request)
    if api_key is None:
        return JsonResponse({"error": "Invalid or missing API key"}, status=401)

    qs = Event.objects.filter(user=api_key.user)

    # Optional filters
    event_type = request.GET.get("type")
    if event_type:
        qs = qs.filter(type=event_type)

    project = request.GET.get("project")
    if project:
        qs = qs.filter(project=project)

    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)

    limit = min(int(request.GET.get("limit", 20)), 100)

    events = [
        {
            "id": e.id,
            "type": e.type,
            "project": e.project,
            "status": e.status,
            "payload": e.payload,
            "source": e.source,
            "created_at": e.created_at.isoformat(),
        }
        for e in qs[:limit]
    ]

    return JsonResponse({"events": events, "count": len(events)})


# EOF
