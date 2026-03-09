#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clew app URLs - Main views."""

from __future__ import annotations

from django.urls import path

from .. import views
from ..views import registry

# Page views + public endpoints
urlpatterns = [
    # Main clew page
    path("", views.clew_index, name="clew_index"),
    # Badge — public SVG (no login required, clean URL for README embedding)
    path("badge/<str:hash_value>/", registry.badge, name="clew_badge"),
]


# EOF
