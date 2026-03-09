#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Root dispatcher — authenticated users see Hub, visitors see landing."""

from __future__ import annotations

from django.shortcuts import redirect

from .index import index_view


def root_dispatch(request):
    """Route / to hub workspace (auth) or landing page (anon/visitor).

    Authenticated non-pool-visitors → workspace (includes readonly-visitor).
    Pool visitors (visitor-NNN) and anonymous → landing page.
    """
    if request.user.is_authenticated:
        # Pool visitors (visitor-001 etc.) see landing
        if request.user.username.startswith("visitor-"):
            return redirect("public_app:landing")
        # Everyone else (logged-in users + readonly-visitor) → workspace
        return index_view(request)
    return redirect("public_app:landing")


# EOF
