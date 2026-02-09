#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifier app URLs package.

Re-exports all URL patterns from submodules for Django URL configuration.
"""

from __future__ import annotations

from .api import urlpatterns as api_patterns
from .index import urlpatterns as index_patterns

app_name = "verifier"

# Combine all URL patterns
urlpatterns = index_patterns + api_patterns


# EOF
