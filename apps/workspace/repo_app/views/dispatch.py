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
      - /chat/ → unified workspace layout with the snake-logo chat pane active
      - /console/, /files/ → workspace shell with that module active
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
    # Route by CANONICAL SESSION ROLE (services/visitor_pool/session_role.py)
    # rather than a bare is_authenticated check, so the intent is explicit:
    #   anonymous           → marketing landing (first-time / not-entered).
    #   user                → workspace launcher.
    #   visitor / readonly  → workspace launcher in GUEST MODE.
    #
    # A first-time browser is ANONYMOUS at "/" because VisitorAutoLoginMiddleware
    # now exact-skips "/" and "/landing/", so it correctly reaches the marketing
    # landing (the bug this fixes). A session only becomes ROLE_VISITOR /
    # ROLE_READONLY_VISITOR after DELIBERATELY entering the workspace (the hero
    # "Enter as visitor" CTA points at /enter/, which auto-allocates a slot);
    # once inside it must STAY inside — the workspace sidebar/dock "Home" links
    # to "/", so bouncing these roles back to marketing would eject an active
    # guest on every Home click (card hub-visitor-ux-allapps, operator-confirmed
    # 2026-07-07; regression-guarded by
    # tests/apps/apps_app/test_launcher_guest_mode.py).
    from apps.infra.project_app.services.visitor_pool import (
        ROLE_ANONYMOUS,
        get_session_role,
    )

    if get_session_role(request) == ROLE_ANONYMOUS:
        return redirect("public_app:landing")

    if session_token is not None:
        request.chat_session_token = str(session_token)

    # /chat/ (and the /chat/<uuid>/ session deep-link) render the unified
    # workspace layout with the CHAT pane active — the good "snake-logo"
    # welcome pane (global_base_partials/workspace_chat_pane.html), driven
    # by the same global-ai-chat + chat-welcome JS as every other page.
    # Setting request.initial_pane makes the sidebar JS open #pane-chat on
    # load. Previously /chat/ redirected to the legacy 3-pane robot shell
    # (workspace_app/shell.html) — now retired for chat (both authenticated
    # and visitor sessions land on the snake pane).
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
