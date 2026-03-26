#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Root dispatcher — authenticated users see Hub, visitors see landing."""

from __future__ import annotations

from django.shortcuts import redirect

from .index import index_view


def root_dispatch(request, pane=None, session_token=None):
    """Route / to hub workspace (auth) or landing page (anon).

    Authenticated users (including all visitor types) → workspace.
    Anonymous → landing page.

    Args:
        pane: Optional initial pane hint ('chat', 'console', 'editor').
              Used by /chat/, /console/, /files/ URL routes.
        session_token: Optional chat session UUID for /chat/<uuid>/ URLs.
    """
    if request.user.is_authenticated:
        # readonly-visitor → landing (read-only fallback, not a real workspace user)
        if request.user.username == "readonly-visitor":
            return redirect("public_app:landing")
        # All other authenticated users (including visitors) go to workspace
        if pane:
            request.initial_pane = pane
        if session_token is not None:
            request.chat_session_token = str(session_token)
        return index_view(request)
    return redirect("public_app:landing")


# EOF
