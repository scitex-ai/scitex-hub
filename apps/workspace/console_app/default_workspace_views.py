"""Default workspace views for Code app."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def user_default_workspace(request):
    """Default workspace for logged-in users without a specific project."""
    context = {
        "username": request.user.username,
        "module_name": "Code",
        "module_icon": "fa-code",
    }
    return render(request, "console_app/default_workspace.html", context)
