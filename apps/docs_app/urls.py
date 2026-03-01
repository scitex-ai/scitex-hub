#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/docs_app/urls.py

from django.urls import path

from . import views

app_name = "docs_app"

urlpatterns = [
    # Documentation landing page
    path("", views.docs_index, name="index"),
    # Fragment content for workspace partial (AJAX)
    path("content/<slug:slug>/", views.docs_content, name="content"),
    # Export documentation as Markdown
    path("export/<slug:slug>/", views.docs_export, name="export"),
    # Python package documentation (scitex PyPI)
    path("python/", views.docs_python, name="python"),
    # REST API documentation
    path("api/", views.docs_api, name="api"),
    # Serve specific documentation pages (for Sphinx assets)
    path("<str:module>/<path:page>", views.docs_page, name="page"),
]

# EOF
