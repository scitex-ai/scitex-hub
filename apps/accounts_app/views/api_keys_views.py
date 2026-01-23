"""API key management views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts_app.models import APIKey


def handle_create_api_key(request):
    """Handle API key creation."""
    name = request.POST.get("name", "").strip()
    scopes = request.POST.getlist("scopes")

    if not name:
        messages.error(request, "API key name is required")
        return False

    api_key_obj, full_key = APIKey.create_key(
        user=request.user,
        name=name,
        scopes=scopes or ["*"],  # Default: full access
    )
    # Store the full key in session to show once
    request.session["new_api_key"] = full_key
    request.session["new_api_key_name"] = name
    messages.success(request, f'API key "{name}" created successfully!')
    return True


def handle_delete_api_key(request):
    """Handle API key deletion."""
    key_id = request.POST.get("key_id")
    try:
        api_key = APIKey.objects.get(id=key_id, user=request.user)
        key_name = api_key.name
        api_key.delete()
        messages.success(request, f'API key "{key_name}" deleted successfully!')
        return True
    except APIKey.DoesNotExist:
        messages.error(request, "API key not found")
        return False


def handle_toggle_api_key(request):
    """Handle API key activation/deactivation."""
    key_id = request.POST.get("key_id")
    try:
        api_key = APIKey.objects.get(id=key_id, user=request.user)
        api_key.is_active = not api_key.is_active
        api_key.save()
        status = "activated" if api_key.is_active else "deactivated"
        messages.success(request, f'API key "{api_key.name}" {status}')
        return True
    except APIKey.DoesNotExist:
        messages.error(request, "API key not found")
        return False


@login_required
def api_keys(request):
    """API key management page."""
    user_api_keys = APIKey.objects.filter(user=request.user).select_related("user")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create":
            handle_create_api_key(request)
        elif action == "delete":
            handle_delete_api_key(request)
        elif action == "toggle":
            handle_toggle_api_key(request)

        return redirect("accounts_app:api_keys")

    # Get newly created key from session (show once)
    new_api_key = request.session.pop("new_api_key", None)
    new_api_key_name = request.session.pop("new_api_key_name", None)

    context = {
        "api_keys": user_api_keys,
        "new_api_key": new_api_key,
        "new_api_key_name": new_api_key_name,
    }
    return render(request, "accounts_app/api_keys.html", context)
