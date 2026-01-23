"""Default workspace views for Scholar app."""

from django.shortcuts import render
from apps.project_app.services.anonymous_storage import get_visitor_storage_path


def guest_session_view(request, username):
    """Guest session workspace for Scholar - supports visitor users."""
    # Handle visitor users
    is_visitor = not request.user.is_authenticated

    if is_visitor:
        # Ensure session exists for visitor users
        if not request.session.session_key:
            request.session.create()

        # Get temporary storage path
        storage_path = get_visitor_storage_path(request.session.session_key)
        display_username = f"guest-{request.session.session_key[:8]}"
    else:
        storage_path = f"/data/users/{request.user.username}/proj/"
        display_username = request.user.username

    context = {
        "is_guest_session": True,
        "guest_username": username,
        "is_visitor": is_visitor,
        "storage_path": storage_path,
        "display_username": display_username,
        "module_name": "Scholar",
        "module_icon": "fa-search",
        "show_save_prompt": is_visitor,  # Show "Sign up to save" prompts
    }
    return render(request, "scholar_app/default_workspace.html", context)


def user_default_workspace(request):
    """Default workspace for logged-in users without a specific project."""
    # Support visitor users accessing this endpoint
    is_visitor = not request.user.is_authenticated

    if is_visitor:
        # Ensure session exists for visitor users
        if not request.session.session_key:
            request.session.create()

        # Get temporary storage path
        storage_path = get_visitor_storage_path(request.session.session_key)
        username = None
        display_username = f"guest-{request.session.session_key[:8]}"
    else:
        storage_path = f"/data/users/{request.user.username}/proj/"
        username = request.user.username
        display_username = username

    context = {
        "is_guest_session": False,
        "is_visitor": is_visitor,
        "username": username,
        "display_username": display_username,
        "storage_path": storage_path,
        "module_name": "Scholar",
        "module_icon": "fa-search",
        "show_save_prompt": is_visitor,  # Show "Sign up to save" prompts
    }
    return render(request, "scholar_app/default_workspace.html", context)
