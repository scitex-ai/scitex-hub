#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub App Index URLs

Main index page for the central project hub.
"""

from django.urls import path

from ..views import index as index_views

# Namespaced so the mount can be reversed (``repo_app:index``) rather than
# guessed. Without it the single route below lands in the root namespace as a
# bare "index", one collision away from resolving to somebody else's page.
app_name = "repo_app"

urlpatterns = [
    # Main index page
    path("", index_views.index_view, name="index"),
]

# EOF
