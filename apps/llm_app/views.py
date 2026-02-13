import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.integrations_app.models import IntegrationConnection
from apps.llm_app.models import LLMConnection
from apps.llm_app.services import UserLLMService


@login_required
@require_http_methods(["GET"])
def api_list_providers(request):
    """List user's configured LLM providers"""
    connections = IntegrationConnection.objects.filter(
        user=request.user,
        service__in=["anthropic", "openai", "local_llm"],
    ).select_related("llm_connection")

    providers = []
    for conn in connections:
        provider_data = {
            "id": conn.id,
            "service": conn.service,
            "service_display": conn.get_service_display(),
            "status": conn.status,
            "created_at": conn.created_at.isoformat(),
        }

        # Add LLM-specific data if available
        if hasattr(conn, "llm_connection"):
            llm_conn = conn.llm_connection
            provider_data.update(
                {
                    "default_model": llm_conn.default_model,
                    "total_requests": llm_conn.total_requests,
                    "total_tokens_used": llm_conn.total_tokens_used,
                    "estimated_cost_usd": float(llm_conn.estimated_cost_usd),
                    "last_request_at": (
                        llm_conn.last_request_at.isoformat()
                        if llm_conn.last_request_at
                        else None
                    ),
                    "daily_request_limit": llm_conn.daily_request_limit,
                    "daily_token_limit": llm_conn.daily_token_limit,
                }
            )

        providers.append(provider_data)

    return JsonResponse({"success": True, "providers": providers})


@login_required
@require_http_methods(["POST"])
def api_add_provider(request):
    """Add a new LLM provider"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    service = data.get("service")
    api_key = data.get("api_key")
    default_model = data.get("default_model", "")

    # Validate required fields
    if not service or service not in ["anthropic", "openai", "local_llm"]:
        return JsonResponse(
            {"success": False, "error": "Invalid or missing service"}, status=400
        )

    if not api_key and service != "local_llm":
        return JsonResponse({"success": False, "error": "API key required"}, status=400)

    # Check if connection already exists
    existing = IntegrationConnection.objects.filter(
        user=request.user, service=service
    ).first()

    if existing:
        return JsonResponse(
            {
                "success": False,
                "error": f"{service} connection already exists. Delete it first to add a new one.",
            },
            status=400,
        )

    try:
        # Create base connection
        connection = IntegrationConnection.objects.create(
            user=request.user,
            service=service,
            status="active",
        )

        # Set API key
        if api_key:
            connection.set_api_key(api_key)
            connection.save()

        # Create LLM-specific connection
        llm_connection = LLMConnection.objects.create(
            connection=connection,
            default_model=default_model,
        )

        return JsonResponse(
            {
                "success": True,
                "provider": {
                    "id": connection.id,
                    "service": connection.service,
                    "service_display": connection.get_service_display(),
                    "status": connection.status,
                    "default_model": llm_connection.default_model,
                },
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Failed to add provider: {str(e)}"},
            status=500,
        )


@login_required
@require_http_methods(["DELETE"])
def api_delete_provider(request, provider_id):
    """Delete an LLM provider connection"""
    try:
        connection = IntegrationConnection.objects.get(
            id=provider_id,
            user=request.user,
            service__in=["anthropic", "openai", "local_llm"],
        )

        service_name = connection.get_service_display()
        connection.delete()

        return JsonResponse(
            {
                "success": True,
                "message": f"{service_name} connection deleted successfully",
            }
        )

    except IntegrationConnection.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Provider not found"}, status=404
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Failed to delete provider: {str(e)}"},
            status=500,
        )


@login_required
@require_http_methods(["POST"])
def api_test_provider(request, provider_id):
    """Test an LLM provider connection"""
    try:
        connection = IntegrationConnection.objects.get(
            id=provider_id,
            user=request.user,
            service__in=["anthropic", "openai", "local_llm"],
        )

        # Try to make a simple test request
        service = UserLLMService(
            user=request.user, preferred_provider=connection.service
        )

        try:
            result = service.complete(
                prompt="Say 'Hello' if you can hear me.",
                app_name="llm_app",
                feature="connection_test",
                max_tokens=10,
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Connection test successful",
                    "response": result["text"],
                    "tokens_used": result["total_tokens"],
                }
            )

        except NotImplementedError:
            # Expected when scitex.llm is not yet implemented
            return JsonResponse(
                {
                    "success": True,
                    "message": "Connection configured (LLM provider not yet implemented)",
                    "note": "API calls will be enabled when scitex.llm module is ready",
                }
            )

        except Exception as e:
            return JsonResponse(
                {"success": False, "error": f"Connection test failed: {str(e)}"},
                status=500,
            )

    except IntegrationConnection.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Provider not found"}, status=404
        )


@login_required
@require_http_methods(["GET"])
def api_get_usage(request):
    """Get usage statistics for user's LLM connections"""
    days = int(request.GET.get("days", 30))

    try:
        service = UserLLMService(user=request.user)

        if not service.connection:
            return JsonResponse(
                {
                    "success": True,
                    "usage": None,
                    "message": "No active LLM connection found",
                }
            )

        stats = service.get_usage_stats(days=days)

        return JsonResponse({"success": True, "usage": stats})

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Failed to get usage stats: {str(e)}"},
            status=500,
        )
