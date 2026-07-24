#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URL patterns for the hub-side scitex-storage security wrapper.

config/urls.py mounts THIS module at ``apps/storage/`` in place of the raw
``scitex_storage._django.urls`` (card sec-working-dir-passthrough-family,
SITE 4). ``app_name`` is kept as the upstream ``scitex_storage`` so any
``{% url 'scitex_storage:index' %}`` reverse keeps resolving.
"""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "scitex_storage"

urlpatterns = [
    path("", views.index, name="index"),
    path("healthz", views.healthz, name="healthz"),
]

# EOF
