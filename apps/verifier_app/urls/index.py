#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifier app URLs - Main views."""

from __future__ import annotations

from django.urls import path

from .. import views

# Page views
urlpatterns = [
    # Main verifier page
    path("", views.verifier_index, name="verifier_index"),
]


# EOF
