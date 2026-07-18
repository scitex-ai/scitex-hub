#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Root dispatcher — authenticated users (incl. visitors) see the launcher."""

from __future__ import annotations

from django.shortcuts import redirect


def root_dispatch(request, pane=None, session_token=None):
    """Route / to the app-launcher home (auth/visitor) or landing page (anon).

    Authenticated regular users:
      - / (no pane) → app-launcher workspace home (approved 2026-07-07 design).
        The previous home (Hub index / Gitea-style project view) stays
        reachable at /apps/home/.
      - /chat/ → the global_base pane system with the snake-logo chat
        welcome active (#pane-chat). NOT the 3-pane workspace shell: its
        robot-icon chat surface is retired (operator, 2026-07-18 —
        "この画面は二度と使えません"), and rendering shell.html here also
        put a SECOND #stx-shell-ai-input on the page (shell.html's own
        copy next to workspace_ai_pane.html's), so the engine bound to
        whichever came first in document order.
      - /console/, /files/ → workspace shell with that module active
        (their standalone replacements land next; see card
        hub-chat-unify-snake-pane).
    Visitor users (visitor-* and readonly-visitor) → launcher in guest mode
    (tiles visible + prominent Sign in / Sign up CTA). Bouncing workspace
    visitors to the marketing landing read as breakage — the sidebar/dock
    "All apps" link must keep them inside the workspace
    (card hub-visitor-ux-allapps, operator-confirmed 2026-07-07).
    TRUE anonymous (no session user) → landing page.

    Args:
        pane: Optional initial pane hint ('chat', 'console', 'editor').
              Used by /chat/, /console/, /files/ URL routes.
        session_token: Optional chat session UUID for /chat/<uuid>/ URLs.
    """
    if request.user.is_authenticated:
        if pane == "chat":
            # request.initial_pane → body[data-initial-pane] in
            # global_base.html; sidebar/index.ts activateInitialPane()
            # reads it first and switches #pane-chat active. This is the
            # attribute's first writer — the read side shipped earlier.
            request.initial_pane = "chat"
            if session_token is not None:
                request.chat_session_token = str(session_token)
            from apps.workspace.apps_app.views.launcher import launcher

            return launcher(request)
        # Other pane-specific URLs → workspace shell with that module
        if pane:
            return redirect("workspace_app:shell_module", module=pane)
        if session_token is not None:
            request.chat_session_token = str(session_token)
        from apps.workspace.apps_app.views.launcher import launcher

        return launcher(request)
    return redirect("public_app:landing")


# EOF
