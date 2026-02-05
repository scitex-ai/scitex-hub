#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public Scholar API URLs - Rate limited endpoints for external access."""

from __future__ import annotations

from django.urls import path

from ..api import public_search

app_name = "public_api"

urlpatterns = [
    path("search/", public_search.search, name="search"),
    path("info/", public_search.info, name="info"),
]

# EOF
