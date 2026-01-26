#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vis app URLs - Page views and figure management."""

from __future__ import annotations

from django.urls import path

from .. import views

# Page views
page_patterns = [
    # Main editor - Vis (VisPlot-inspired, now default)
    path("", views.figure_editor, name="figure_editor"),
    # Gallery page - shows all available plot types
    path("gallery/", views.gallery_page, name="gallery"),
    # Legacy canvas-based editor
    path("legacy/", views.figure_editor_legacy, name="figure_editor_legacy"),
]

# Figure management
figure_patterns = [
    path("figures/", views.figure_list, name="figure_list"),
    path("figures/create/", views.create_figure, name="create_figure"),
    path("figures/<uuid:figure_id>/", views.figure_detail, name="figure_detail"),
]

urlpatterns = page_patterns + figure_patterns


# EOF
