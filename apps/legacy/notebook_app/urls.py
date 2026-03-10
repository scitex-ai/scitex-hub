#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notebook module URL patterns."""

from django.urls import path

from . import views

app_name = "notebook_app"

urlpatterns = [
    path("", views.index_view, name="index"),
]

# EOF
