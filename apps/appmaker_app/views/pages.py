jjj
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App Maker — page views (my_modules list, code editor)."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.project_app.services.project_utils import get_current_project

from ..models import UserModule


@login_required
def my_modules(request):
    """List the current user's modules."""
    current_project = get_current_project(request)
    modules = UserModule.objects.filter(author=request.user, is_active=True)
    return render(
        request,
        "appmaker_app/my_modules.html",
        {
            "current_project": current_project,
            "modules": modules,
        },
    )


@login_required
def editor(request, slug=None):
    """Code editor page for creating or editing a module."""
    current_project = get_current_project(request)
    user_module = None
    if slug:
        user_module = get_object_or_404(
            UserModule, slug=slug, author=request.user, is_active=True
        )

    from apps.apps_app.models import CATEGORY_CHOICES

    return render(
        request,
        "appmaker_app/editor.html",
        {
            "current_project": current_project,
            "module": user_module,
            "category_choices": CATEGORY_CHOICES,
        },
    )


# EOF
