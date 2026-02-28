#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Root dispatcher — authenticated users see Hub, others see landing page."""

from __future__ import annotations

from apps.public_app.views import index as landing_view

from .index import index_view


def root_dispatch(request):
    """Route / to hub dashboard (auth) or landing page (anon)."""
    if request.user.is_authenticated:
        return index_view(request)
    return landing_view(request)


# EOF
