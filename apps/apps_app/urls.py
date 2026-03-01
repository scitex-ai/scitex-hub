#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apps URL configuration."""

from django.urls import path

from . import views

urlpatterns = [
    # Pages
    path("", views.browse, name="browse"),
    path("my/", views.my_modules, name="my_modules"),
    path("review/", views.review_queue, name="review_queue"),
    # API — must come before <str:module_name> catch-all
    path("api/reorder/", views.api_reorder, name="api_reorder"),
    path("api/<str:module_name>/install/", views.api_install, name="api_install"),
    path("api/<str:module_name>/uninstall/", views.api_uninstall, name="api_uninstall"),
    path("api/<str:module_name>/toggle/", views.api_toggle, name="api_toggle"),
    path("api/<str:module_name>/star/", views.api_star, name="api_star"),
    path("api/<str:module_name>/unstar/", views.api_unstar, name="api_unstar"),
    path("api/<str:module_name>/review/", views.api_review, name="api_review"),
    path(
        "api/<str:module_name>/config/",
        views.api_update_config,
        name="api_update_config",
    ),
    path(
        "api/<str:module_name>/submit/", views.api_submit_for_review, name="api_submit"
    ),
    path(
        "api/submissions/<int:submission_id>/review/",
        views.api_review_submission,
        name="api_review_submission",
    ),
    # Detail — catch-all last
    path("<str:module_name>/", views.detail, name="detail"),
]


# EOF
