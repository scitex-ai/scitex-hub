#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Terminal model-provider picker API (thin view).

``GET /apps/console/api/terminal/providers/`` returns the server-side
provider registry (ids + labels), whether the picker is enabled for the
current session role, and per-provider key PRESENCE (a boolean — the key
value itself is never serialized). All policy lives in
``services.terminal_provider``; this view only shapes JSON.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.services.visitor_pool.session_role import (
    ROLE_READONLY_VISITOR,
    get_session_role,
)
from apps.workspace.console_app.services.terminal_provider import (
    AI_PROVIDER_SETTINGS_URL,
    DEFAULT_PROVIDER,
    TERMINAL_PROVIDERS,
)


@require_http_methods(["GET"])
def api_terminal_providers(request):
    """List selectable terminal providers for the current session."""
    role = get_session_role(request)
    picker_enabled = getattr(request.user, "is_authenticated", False)
    reason = ""
    if not picker_enabled:
        reason = "Sign in to use an alternative model provider."
    elif role == ROLE_READONLY_VISITOR:
        picker_enabled = False
        reason = (
            "Read-only visitor sessions cannot use API-key providers — "
            "sign up or log in to use your own key."
        )

    stored_services: set = set()
    if picker_enabled:
        from apps.infra.integrations_app.models import IntegrationConnection

        key_services = {
            entry["key_service"]
            for entry in TERMINAL_PROVIDERS.values()
            if entry["key_service"]
        }
        stored_services = set(
            IntegrationConnection.objects.filter(
                user=request.user, service__in=key_services
            )
            .exclude(api_key="")
            .values_list("service", flat=True)
        )

    providers = [
        {
            "id": provider_id,
            "label": entry["label"],
            "requires_key": entry["key_service"] is not None,
            "has_key": (
                entry["key_service"] is None
                or entry["key_service"] in stored_services
            ),
        }
        for provider_id, entry in TERMINAL_PROVIDERS.items()
    ]
    return JsonResponse(
        {
            "success": True,
            "default": DEFAULT_PROVIDER,
            "picker_enabled": picker_enabled,
            "picker_disabled_reason": reason,
            "key_settings_url": AI_PROVIDER_SETTINGS_URL,
            "providers": providers,
        }
    )


# EOF
