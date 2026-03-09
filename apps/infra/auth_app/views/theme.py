#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Theme preference API views."""
from __future__ import annotations
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json

from ..models import UserProfile


@require_POST
def api_save_theme_preference(request):
    """
    API endpoint to save user's theme preference.

    POST /auth/api/save-theme/
    Body: {
        "theme": "light" | "dark",
        "code_theme_light": "atom-one-light",  // optional
        "code_theme_dark": "dracula"  // optional
    }
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {"success": False, "error": "Not authenticated"}, status=401
        )

    try:
        data = json.loads(request.body)
        theme = data.get("theme")
        code_theme_light = data.get("code_theme_light")
        code_theme_dark = data.get("code_theme_dark")
        editor_theme_light = data.get("editor_theme_light")
        editor_theme_dark = data.get("editor_theme_dark")

        # Validate theme
        if theme and theme not in ["light", "dark"]:
            return JsonResponse(
                {"success": False, "error": "Invalid theme"}, status=400
            )

        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=request.user)

        # Update theme preferences
        if theme:
            profile.theme_preference = theme
        if code_theme_light:
            profile.code_theme_light = code_theme_light
        if code_theme_dark:
            profile.code_theme_dark = code_theme_dark
        if editor_theme_light:
            profile.editor_theme_light = editor_theme_light
        if editor_theme_dark:
            profile.editor_theme_dark = editor_theme_dark

        profile.save()

        return JsonResponse(
            {
                "success": True,
                "theme": profile.theme_preference,
                "code_theme_light": profile.code_theme_light,
                "code_theme_dark": profile.code_theme_dark,
                "editor_theme_light": profile.editor_theme_light,
                "editor_theme_dark": profile.editor_theme_dark,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def api_get_theme_preference(request):
    """
    API endpoint to get user's theme preference.

    GET /auth/api/get-theme/
    Returns: {
        "theme": "light" | "dark",
        "code_theme_light": "atom-one-light",
        "code_theme_dark": "dracula"
    }
    """
    if not request.user.is_authenticated:
        # Return defaults for visitor users
        return JsonResponse(
            {
                "theme": "dark",
                "code_theme_light": "atom-one-light",
                "code_theme_dark": "nord",
                "editor_theme_light": "neat",
                "editor_theme_dark": "nord",
            }
        )

    try:
        profile = request.user.auth_profile
        return JsonResponse(
            {
                "theme": profile.theme_preference,
                "code_theme_light": profile.code_theme_light,
                "code_theme_dark": profile.code_theme_dark,
                "editor_theme_light": profile.editor_theme_light,
                "editor_theme_dark": profile.editor_theme_dark,
            }
        )
    except UserProfile.DoesNotExist:
        # Profile doesn't exist yet, return defaults
        return JsonResponse(
            {
                "theme": "dark",
                "code_theme_light": "atom-one-light",
                "code_theme_dark": "nord",
                "editor_theme_light": "neat",
                "editor_theme_dark": "nord",
            }
        )


# EOF
