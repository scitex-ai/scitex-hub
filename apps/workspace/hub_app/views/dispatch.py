#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Root dispatcher — authenticated users see Hub, visitors see landing."""

from __future__ import annotations

from django.shortcuts import redirect

from .index import index_view


def root_dispatch(request):
    """Route / to hub workspace (auth) or landing page (anon).

    Authenticated users (including all visitor types) → workspace.
    Anonymous → landing page.
    """
    if request.user.is_authenticated:
        return index_view(request)
    return redirect("public_app:landing")


# EOF
