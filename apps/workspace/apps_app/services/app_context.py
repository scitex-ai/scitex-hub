#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic context builder for user-submitted apps.

Provides the minimal context every user app partial needs.
"""

from __future__ import annotations


def build_user_app_context(request, current_project=None):
    """Build template context for a user app partial.

    Called by the workspace registry's context_builder for dynamically
    loaded user apps.
    """
    return {
        "current_project": current_project,
        "user": request.user if hasattr(request, "user") else None,
    }


# EOF
