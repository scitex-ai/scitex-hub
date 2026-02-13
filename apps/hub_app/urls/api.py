#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub App API URLs

API endpoints for the hub.
"""

from django.urls import path

from ..views import api as api_views

urlpatterns = [
    # Project listing
    path("projects/", api_views.api_projects_list, name="api_projects_list"),
    # Activity feed
    path("activity/", api_views.api_activity_feed, name="api_activity_feed"),
]

# EOF
