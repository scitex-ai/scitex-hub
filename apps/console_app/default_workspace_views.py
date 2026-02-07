"""Default workspace views for Code app."""

from django.shortcuts import render


def guest_session_view(request, username):
    """Guest session workspace for Code."""
    context = {
        "is_guest_session": True,
        "guest_username": username,
        "module_name": "Code",
        "module_icon": "fa-code",
    }
    return render(request, "console_app/default_workspace.html", context)


def user_default_workspace(request):
    """Default workspace for logged-in users without a specific project."""
    context = {
        "is_guest_session": False,
        "username": request.user.username if request.user.is_authenticated else None,
        "module_name": "Code",
        "module_icon": "fa-code",
    }
    return render(request, "console_app/default_workspace.html", context)
