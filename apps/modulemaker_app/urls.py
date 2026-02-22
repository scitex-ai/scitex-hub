#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module Maker URL configuration."""

from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    # Pages
    path("", views.my_modules, name="my_modules"),
    path("new/", views.editor, name="editor_new"),
    path("<slug:slug>/edit/", views.editor, name="editor"),
    # API
    path("api/create/", views.api_create_module, name="api_create"),
    path("api/<slug:slug>/update/", views.api_update_module, name="api_update"),
    path("api/<slug:slug>/run/", views.api_run_module, name="api_run"),
    path("api/<slug:slug>/delete/", views.api_delete_module, name="api_delete"),
]


# EOF
