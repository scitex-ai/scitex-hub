#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clew app URLs package.

Re-exports all URL patterns from submodules for Django URL configuration.
"""

from __future__ import annotations

from django.urls import include, path

from .api import urlpatterns as api_patterns
from .index import urlpatterns as index_patterns

app_name = "clew_app"

# Combine: index pages at root, API under api/ prefix
urlpatterns = index_patterns + [
    path("api/", include(api_patterns)),
]


# EOF
