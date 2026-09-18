from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.infra.llm_app.funded_chat.config import (
    FundedChatConfig,
    FundedChatConfigurationError,
    load_funded_chat_config,
)
from apps.infra.llm_app.funded_chat.service import FundedChatService


@login_required
@never_cache
@require_GET
def api_funded_chat_allowance(request):
    """Return the authenticated user's UTC funded allowance contract."""

    try:
        config = load_funded_chat_config()
    except FundedChatConfigurationError:
        disabled = FundedChatConfig(
            enabled=False,
            provider="",
            model="",
            api_key="",
        )
        snapshot = FundedChatService(config=disabled).snapshot(request.user)
        return JsonResponse(snapshot.as_payload(), status=503)

    snapshot = FundedChatService(config=config).snapshot(request.user)
    status = 200
    if snapshot.remaining is None:
        status = 503 if snapshot.category == "provider_outage" else 403
    return JsonResponse(snapshot.as_payload(), status=status)
