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
from .scholar_django import urlpatterns as scholar_django_patterns
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
    # The upstream scitex-scholar UI, behind hub's login. Mounted at
    # /apps/scholar/v2/ ALONGSIDE the legacy routes above, not in place of
    # them — same gradual cut-over shape writer used (#146), so the page the
    # operator is looking at right now does not change under him. Flipping the
    # default is a separate, one-line decision once the leaf has been read on a
    # running site. See scholar_django.py for why the gate is not optional.
    + scholar_django_patterns
)


# EOF
