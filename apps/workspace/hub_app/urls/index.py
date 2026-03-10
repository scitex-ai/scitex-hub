#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub App Index URLs

Main index page for the central project hub.
"""

from django.urls import path

from ..views import index as index_views

urlpatterns = [
    # Main index page
    path("", index_views.index_view, name="index"),
]

# EOF
