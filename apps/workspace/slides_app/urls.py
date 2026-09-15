#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Slides App URL configuration."""

from django.urls import path

from . import views

app_name = "slides_app"

urlpatterns = [
    path("", views.slides_index, name="index"),
    path("api/decks/", views.api_decks, name="api_decks"),
    path("api/deck/", views.api_deck, name="api_deck"),
    path(
        "api/deck/from-project/",
        views.api_deck_from_project,
        name="api_deck_from_project",
    ),
    path("api/file/", views.api_file, name="api_file"),
]

# EOF
