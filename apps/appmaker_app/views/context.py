#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App Maker — context builder for workspace tab integration."""

from __future__ import annotations

from ..models import UserModule


def build_usermod_context(request, current_project=None):
    """Context builder for App Maker workspace tab.

    Called by the workspace registry for AJAX partial loading.
    Returns the user's modules list for the my_modules_partial template.
    """
    if request.user.is_authenticated:
        modules = UserModule.objects.filter(author=request.user, is_active=True)
    else:
        modules = UserModule.objects.none()

    return {
        "current_project": current_project,
        "modules": modules,
    }


# EOF
