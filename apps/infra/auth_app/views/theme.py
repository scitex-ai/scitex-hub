#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Theme preference API views.

Theme resolution contract:

- The BASE default is DARK for every first visit, on every viewport.
- Only a REGISTERED user's saved profile preference is served as a
  preference (``source: "profile"``); everything else is served as a
  default (``source: "default"``) so the client can let an explicit
  prior localStorage choice win over it.
"""
from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from ..models import UserProfile

#: First-visit defaults. DARK is the operator-mandated base default;
#: ``source: "default"`` tells the client this is NOT a saved
#: preference (an explicit prior localStorage choice may win over it).
_DEFAULT_THEME_RESPONSE = {
    "theme": "dark",
    "code_theme_light": "atom-one-light",
    "code_theme_dark": "nord",
    "editor_theme_light": "neat",
    "editor_theme_dark": "nord",
    "source": "default",
}


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
                "persisted": True,
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
        "code_theme_dark": "dracula",
        "source": "profile" | "default"
    }

    ``source: "profile"`` only for an authenticated user's saved row.
    """
    if not request.user.is_authenticated:
        return JsonResponse(dict(_DEFAULT_THEME_RESPONSE))

    try:
        profile = request.user.auth_profile
        return JsonResponse(
            {
                "theme": profile.theme_preference,
                "code_theme_light": profile.code_theme_light,
                "code_theme_dark": profile.code_theme_dark,
                "editor_theme_light": profile.editor_theme_light,
                "editor_theme_dark": profile.editor_theme_dark,
                "source": "profile",
            }
        )
    except UserProfile.DoesNotExist:
        # Profile doesn't exist yet, return defaults
        return JsonResponse(dict(_DEFAULT_THEME_RESPONSE))


# EOF
