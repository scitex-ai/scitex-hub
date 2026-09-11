#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Theme preference API views.

Theme resolution contract (card hub-theme-default-must-be-dark):

- The BASE default is DARK for every first visit, on every viewport.
- Only a REGISTERED user's saved profile preference is served as a
  preference (``source: "profile"``); everything else is served as a
  default (``source: "default"``) so the client can let an explicit
  prior localStorage choice win over it.
- Visitor-pool sessions (writable ``visitor-NNN`` slots and the shared
  ``readonly-visitor``) are RECYCLED accounts: their profile rows carry
  whatever theme a PREVIOUS visitor happened to save, not this
  visitor's preference. Serving that row as a saved preference is how
  one stale ``light`` poisoned every later visitor allocated the same
  slot (prod measurement 2026-07-22). Visitors therefore always get
  the defaults, and their toggles are never persisted onto the shared
  account (the choice still sticks per-browser via localStorage).
"""
from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.infra.project_app.services.visitor_pool import is_visitor_session

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

    if is_visitor_session(request):
        # A visitor's toggle must NOT be written onto the recycled pool
        # account — it would become the NEXT visitor's "preference".
        # The choice still sticks for this browser via localStorage
        # (the client writes localStorage before calling this API).
        return JsonResponse(
            {
                "success": True,
                "persisted": False,
                "scope": "browser",
                "reason": "visitor-session",
            }
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

    ``source: "profile"`` only for a REGISTERED user's saved row.
    Anonymous AND visitor-pool sessions get the dark defaults: a
    recycled pool account's profile row is a previous visitor's
    leftover, never this visitor's preference.
    """
    if not request.user.is_authenticated or is_visitor_session(request):
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
