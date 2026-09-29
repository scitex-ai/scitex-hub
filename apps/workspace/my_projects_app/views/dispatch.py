#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Root dispatcher for marketing and authenticated workspace routes."""

from __future__ import annotations

from django.shortcuts import redirect


def root_dispatch(request, pane=None, session_token=None):
    """Route authenticated users to the workspace and signed-out users away.

    Authenticated regular users:
      - / (no pane) → app-launcher workspace home (approved 2026-07-07 design).
        The previous home (Hub index / Gitea-style project view) stays
        reachable at /apps/my-projects/.
      - /chat/ → unified workspace layout with the snake-logo chat pane active
      - /console/, /files/ → workspace shell with that module active
    The bare root remains the marketing entry. Any signed-out attempt to enter
    the workspace is refused to signup; no session key or shared user can
    manufacture project access.

    Args:
        pane: Optional initial pane hint ('chat', 'console', 'editor').
              Used by /chat/, /console/, /files/ URL routes.
        session_token: Optional chat session UUID for /chat/<uuid>/ URLs.
    """
    if not request.user.is_authenticated:
        if request.path.rstrip("/") in ("", "/landing"):
            return redirect("public_app:landing")
        return redirect("auth_app:signup")

    if session_token is not None:
        request.chat_session_token = str(session_token)

    # /chat/ (and the /chat/<uuid>/ session deep-link) render the unified
    # workspace layout with the CHAT pane active — the good "snake-logo"
    # welcome pane (global_base_partials/workspace_chat_pane.html), driven
    # by the same global-ai-chat + chat-welcome JS as every other page.
    # Setting request.initial_pane makes the sidebar JS open #pane-chat on
    # load. Previously /chat/ redirected to the legacy 3-pane robot shell.
    if pane == "chat":
        request.initial_pane = "chat"
        from apps.workspace.apps_app.views.launcher import launcher

        return launcher(request)

    # Other pane-specific URLs (/console/, /files/) keep the shell —
    # those are separate lanes and are intentionally left untouched.
    if pane:
        return redirect("workspace_app:shell_module", module=pane)

    from apps.workspace.apps_app.views.launcher import launcher

    return launcher(request)


# EOF
