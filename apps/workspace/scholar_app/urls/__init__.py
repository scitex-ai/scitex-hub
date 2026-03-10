#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar app URLs package.

Re-exports all URL patterns from submodules for Django URL configuration.
"""

from __future__ import annotations

from .api import urlpatterns as api_patterns
from .bibtex import urlpatterns as bibtex_patterns
from .library import urlpatterns as library_patterns
from .repository import urlpatterns as repository_patterns
from .search import urlpatterns as search_patterns
from .workspace import urlpatterns as workspace_patterns

app_name = "scholar_app"

# Combine all URL patterns
urlpatterns = (
    workspace_patterns
    + search_patterns
    + library_patterns
    + bibtex_patterns
    + repository_patterns
    + api_patterns
)


# EOF
