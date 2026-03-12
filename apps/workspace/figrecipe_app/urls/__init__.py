#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vis app URLs package.

Re-exports all URL patterns from submodules for Django URL configuration.
"""

from __future__ import annotations

from .bundles import urlpatterns as bundle_patterns
from .editor import urlpatterns as editor_patterns
from .figrecipe import urlpatterns as figrecipe_patterns
from .figures import urlpatterns as figure_patterns
from .gallery import urlpatterns as gallery_patterns
from .pages import urlpatterns as page_patterns
from .stats import urlpatterns as stats_patterns
from .style import urlpatterns as style_patterns

app_name = "figrecipe_app"

# Combine all URL patterns
urlpatterns = (
    page_patterns
    + figure_patterns
    + editor_patterns
    + figrecipe_patterns
    + style_patterns
    + gallery_patterns
    + stats_patterns
    + bundle_patterns
)


# EOF
