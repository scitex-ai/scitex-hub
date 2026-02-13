#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clew app URLs - Main views."""

from __future__ import annotations

from django.urls import path

from .. import views

# Page views
urlpatterns = [
    # Main clew page
    path("", views.clew_index, name="clew_index"),
]


# EOF
