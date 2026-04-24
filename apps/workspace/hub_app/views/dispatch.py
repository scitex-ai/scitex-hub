#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Root dispatcher — authenticated users see Hub, visitors see landing."""

from __future__ import annotations

from django.shortcuts import redirect

from .index import index_view


def root_dispatch(request, pane=None, session_token=None):
    """Route / to hub workspace (auth) or landing page (anon/visitor).

    Authenticated regular users:
      - / (no pane) → Hub index (Gitea-style project view)
      - /console/, /chat/, /files/ → workspace shell with that module active
    Visitor users (visitor-* and readonly-visitor) → landing page.
    Anonymous → landing page.

    Args:
        pane: Optional initial pane hint ('chat', 'console', 'editor').
              Used by /chat/, /console/, /files/ URL routes.
        session_token: Optional chat session UUID for /chat/<uuid>/ URLs.
    """
    if request.user.is_authenticated:
        # Visitor users → landing page (they should browse as guests first)
        if (
            request.user.username == "readonly-visitor"
            or request.user.username.startswith("visitor-")
        ):
            return redirect("public_app:landing")
        # Pane-specific URLs → workspace shell with that module
        if pane:
            return redirect("workspace_app:shell_module", module=pane)
        if session_token is not None:
            request.chat_session_token = str(session_token)
        return index_view(request)
    return redirect("public_app:landing")


# EOF
