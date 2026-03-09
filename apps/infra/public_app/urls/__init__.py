#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Public App URL Configuration

Routes are organized into sub-modules:
- pages: All template-serving and page views
- api: All REST API endpoints
- tools: Research tool page views
"""

from django.urls import include, path

app_name = "public_app"

urlpatterns = [
    # REST API endpoints
    path("", include("apps.infra.public_app.urls.api")),
    # Page/template-serving views (must come after API routes)
    path("", include("apps.infra.public_app.urls.pages")),
]
