#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub App API URLs

API endpoints for the hub.
"""

from django.urls import path

from ..views import api as api_views
from ..views import api_browse as browse_views
from ..views import api_user as user_views

urlpatterns = [
    # Me tab
    path("me/", user_views.api_me, name="api_me"),
    # Project listing
    path("projects/", api_views.api_projects_list, name="api_projects_list"),
    # Activity feed
    path("activity/", api_views.api_activity_feed, name="api_activity_feed"),
    # Browse project files inline
    path("browse/", browse_views.api_browse, name="api_browse"),
    # View file content inline
    path("file/", browse_views.api_file_view, name="api_file_view"),
    # Tab content (inline rendering)
    path("issues/", api_views.api_issues, name="api_issues"),
    path("pulls/", api_views.api_pulls, name="api_pulls"),
    path("settings/", api_views.api_settings, name="api_settings"),
    path(
        "account-settings/",
        api_views.api_account_settings,
        name="api_account_settings",
    ),
    # Project switching
    path("select-project/", api_views.api_select_project, name="api_select_project"),
    path(
        "set-active-project/",
        api_views.api_set_active_project,
        name="api_set_active_project",
    ),
    path(
        "projects-overview/",
        api_views.api_projects_overview,
        name="api_projects_overview",
    ),
    # Explore
    path("explore/", api_views.api_explore, name="api_explore"),
    path("user-profile/", user_views.api_user_profile, name="api_user_profile"),
    path("avatar-upload/", user_views.api_avatar_upload, name="api_avatar_upload"),
    path("update-topics/", user_views.api_update_topics, name="api_update_topics"),
    path("update-about/", user_views.api_update_about, name="api_update_about"),
]

# EOF
