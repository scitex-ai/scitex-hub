"""AI Providers settings page - manage LLM API key connections."""

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.infra.integrations_app.models import IntegrationConnection
from apps.infra.llm_app.models import LLMConnection
from apps.infra.llm_app.utils import ALL_LLM_SERVICE_IDS, LLM_PROVIDERS


def _mask_key(key):
    """Mask API key for display: show first 4 and last 4 chars."""
    if not key or len(key) < 8:
        return None
    return f"{key[:4]}...{key[-4:]}"


def _handle_create(request):
    """Handle creating a new LLM provider connection."""
    service = request.POST.get("service", "").strip()
    api_key = request.POST.get("api_key", "").strip()
    default_model = request.POST.get("default_model", "").strip()

    if not service or service not in ALL_LLM_SERVICE_IDS:
        messages.error(request, "Please select a valid provider.")
        return

    needs_key = LLM_PROVIDERS.get(service, {}).get("needs_key", True)
    if not api_key and needs_key:
        messages.error(request, "API key is required.")
        return

    existing = IntegrationConnection.objects.filter(
        user=request.user, service=service
    ).first()
    if existing:
        messages.error(
            request,
            f"{existing.get_service_display()} is already connected. Delete it first.",
        )
        return

    connection = IntegrationConnection.objects.create(
        user=request.user,
        service=service,
        status="active",
    )
    if api_key:
        connection.set_api_key(api_key)
        connection.save()

    LLMConnection.objects.create(
        connection=connection,
        default_model=default_model,
    )
    messages.success(
        request, f"{connection.get_service_display()} connected successfully!"
    )


def _handle_update_limits(request):
    """Handle updating rate limits for an LLM provider."""
    provider_id = request.POST.get("provider_id")
    try:
        conn = IntegrationConnection.objects.get(
            id=provider_id,
            user=request.user,
            service__in=tuple(ALL_LLM_SERVICE_IDS),
        )
        llm = conn.llm_connection
        cost_str = request.POST.get("daily_cost_limit_usd", "").strip()
        try:
            llm.daily_cost_limit_usd = Decimal(cost_str) if cost_str else None
        except InvalidOperation:
            messages.error(request, "Invalid cost value.")
            return
        llm.save(update_fields=["daily_cost_limit_usd"])
        messages.success(request, "Rate limits updated.")
    except IntegrationConnection.DoesNotExist:
        messages.error(request, "Provider not found.")


def _handle_delete(request):
    """Handle deleting an LLM provider connection."""
    provider_id = request.POST.get("provider_id")
    try:
        connection = IntegrationConnection.objects.get(
            id=provider_id,
            user=request.user,
            service__in=tuple(ALL_LLM_SERVICE_IDS),
        )
        name = connection.get_service_display()
        connection.delete()
        messages.success(request, f"{name} disconnected.")
    except IntegrationConnection.DoesNotExist:
        messages.error(request, "Provider not found.")


@login_required
def ai_providers(request):
    """AI Providers settings page."""
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            _handle_create(request)
        elif action == "update_limits":
            _handle_update_limits(request)
        elif action == "delete":
            _handle_delete(request)
        return redirect("accounts_app:ai_providers")

    connections = (
        IntegrationConnection.objects.filter(
            user=request.user,
            service__in=tuple(ALL_LLM_SERVICE_IDS),
        )
        .select_related("llm_connection")
        .order_by("-created_at")
    )

    providers = []
    for conn in connections:
        data = {
            "id": conn.id,
            "service": conn.service,
            "service_display": conn.get_service_display(),
            "status": conn.status,
            "masked_key": _mask_key(conn.get_api_key()),
            "default_model": "",
            "total_requests": 0,
            "total_tokens_used": 0,
            "estimated_cost_usd": 0,
            "daily_cost_limit_usd": None,
        }
        if hasattr(conn, "llm_connection"):
            llm = conn.llm_connection
            data.update(
                {
                    "default_model": llm.default_model,
                    "total_requests": llm.total_requests,
                    "total_tokens_used": llm.total_tokens_used,
                    "estimated_cost_usd": llm.estimated_cost_usd,
                    "daily_cost_limit_usd": llm.daily_cost_limit_usd,
                }
            )
        providers.append(data)

    # Inline available providers so the dropdown renders without an API call
    import json

    from apps.infra.llm_app.utils import get_all_providers_cached

    available_providers = get_all_providers_cached()

    return render(
        request,
        "accounts_app/ai_providers.html",
        {
            "providers": providers,
            "available_providers_json": json.dumps(available_providers),
        },
    )


def _get_active_llm(user):
    """Get the active LLM connection for a user, or None."""
    from apps.infra.llm_app.services import UserLLMService

    svc = UserLLMService(user)
    if svc.connection and svc.llm_connection:
        return svc.llm_connection
    return None


@login_required
@require_http_methods(["GET", "POST"])
def ai_limits_api(request):
    """AJAX endpoint for reading/saving daily limits from the AI panel Config tab.

    GET  → returns current limits for the active provider
    POST → updates limits, synced with /accounts/settings/ai-providers/
    """
    import json
    from decimal import Decimal, InvalidOperation

    from django.http import JsonResponse

    llm = _get_active_llm(request.user)
    if not llm:
        return JsonResponse(
            {
                "success": False,
                "configured": False,
                "configure_url": "/accounts/settings/ai-providers/",
            }
        )

    if request.method == "GET":
        return JsonResponse(
            {
                "success": True,
                "configured": True,
                "limits": {
                    "daily_request_limit": llm.daily_request_limit,
                    "daily_token_limit": llm.daily_token_limit,
                    "daily_cost_limit_usd": (
                        float(llm.daily_cost_limit_usd)
                        if llm.daily_cost_limit_usd is not None
                        else None
                    ),
                },
            }
        )

    # POST — update limits
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    update_fields = []

    for field in ("daily_request_limit", "daily_token_limit"):
        if field in data:
            val = data[field]
            setattr(llm, field, int(val) if val not in (None, "", "null") else None)
            update_fields.append(field)

    if "daily_cost_limit_usd" in data:
        val = data["daily_cost_limit_usd"]
        try:
            llm.daily_cost_limit_usd = (
                Decimal(str(val)) if val not in (None, "", "null") else None
            )
        except InvalidOperation:
            return JsonResponse({"error": "Invalid cost value"}, status=400)
        update_fields.append("daily_cost_limit_usd")

    if update_fields:
        llm.save(update_fields=update_fields)

    return JsonResponse({"success": True})
