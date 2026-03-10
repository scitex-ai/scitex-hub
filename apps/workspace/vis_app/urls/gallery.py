#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vis app URLs - Gallery API endpoints."""

from __future__ import annotations

from django.urls import path

from ..views import api as api_views

# Gallery API endpoints (plot type thumbnails)
gallery_patterns = [
    path("api/gallery/", api_views.get_plot_galleries, name="api_gallery"),
    path(
        "api/gallery/categories/",
        api_views.get_categories,
        name="api_gallery_categories",
    ),
    path(
        "api/gallery/<str:gallery_id>/<str:plot_id>/thumbnail/",
        api_views.get_plot_thumbnail,
        name="api_gallery_thumbnail",
    ),
    path(
        "api/gallery/<str:gallery_id>/<str:plot_id>/template/",
        api_views.get_plot_template,
        name="api_gallery_template",
    ),
]

# Project-based gallery endpoints
project_gallery_patterns = [
    path(
        "api/gallery/generate/",
        api_views.generate_project_gallery,
        name="api_gallery_generate",
    ),
    path(
        "api/gallery/project/",
        api_views.get_project_gallery,
        name="api_gallery_project",
    ),
    path(
        "api/gallery/project/<str:category>/<str:plot_name>/image/",
        api_views.get_project_gallery_image,
        name="api_gallery_project_image",
    ),
    path(
        "api/gallery/project/<str:category>/<str:plot_name>/csv/",
        api_views.get_project_gallery_csv,
        name="api_gallery_project_csv",
    ),
    path(
        "api/gallery/available/",
        api_views.list_gallery_categories_available,
        name="api_gallery_available",
    ),
    # Axis metadata for snap/align by axis position
    path(
        "api/gallery/metadata/<str:category>/<str:plot_name>/",
        api_views.get_plot_metadata,
        name="api_gallery_metadata",
    ),
]

urlpatterns = gallery_patterns + project_gallery_patterns


# EOF
