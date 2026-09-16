#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interest in a planned (Coming-soon) app: "Notify me" or "Build this app"."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from ..models import PlannedAppInterest
from ..planned_apps import PLANNED_BY_ID

_KINDS = {kind for kind, _label in PlannedAppInterest.KIND_CHOICES}


def record_planned_app_interest(user, app_id: str, kind: str) -> bool:
    """Record the interest once per user, app and kind; True when it is new."""
    _interest, created = PlannedAppInterest.objects.get_or_create(
        user=user, app_id=app_id, kind=kind
    )
    return created


@login_required
@require_POST
def api_planned_interest(request, app_id: str):
    kind = request.POST.get("kind", "notify")
    if app_id not in PLANNED_BY_ID or kind not in _KINDS:
        return JsonResponse({"success": False, "error": "Unknown app or kind."}, status=404)
    created = record_planned_app_interest(request.user, app_id, kind)
    return JsonResponse({"success": True, "created": created})


# EOF
