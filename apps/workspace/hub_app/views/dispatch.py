#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Root dispatcher — authenticated users see Hub, visitors see landing."""

from __future__ import annotations

from django.shortcuts import redirect

from .index import index_view


def root_dispatch(request, pane=None, session_id=None):
    """Route / to hub workspace (auth) or landing page (anon).

    Authenticated users (including all visitor types) → workspace.
    Anonymous → landing page.

    Args:
        pane: Optional initial pane hint ('chat', 'console', 'editor').
              Used by /chat/, /console/, /files/ URL routes.
        session_id: Optional chat session ID for /chat/<id>/ URLs.
    """
    if request.user.is_authenticated:
        if pane:
            request.initial_pane = pane
        if session_id is not None:
            request.chat_session_id = session_id
        return index_view(request)
    return redirect("public_app:landing")


# EOF
