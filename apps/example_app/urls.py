#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example module URL patterns."""

from django.urls import path

from . import views

app_name = "example_app"

urlpatterns = [
    path("", views.index_view, name="index"),
]

# EOF
