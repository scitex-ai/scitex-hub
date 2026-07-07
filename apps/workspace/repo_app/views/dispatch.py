#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Root dispatcher — authenticated users see the app launcher, visitors landing."""

from __future__ import annotations

from django.shortcuts import redirect


def root_dispatch(request, pane=None, session_token=None):
    """Route / to the app-launcher home (auth) or landing page (anon/visitor).

    Authenticated regular users:
      - / (no pane) → app-launcher workspace home (approved 2026-07-07 design).
        The previous home (Hub index / Gitea-style project view) stays
        reachable at /apps/home/.
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
        from apps.workspace.apps_app.views.launcher import launcher

        return launcher(request)
    return redirect("public_app:landing")


# EOF
