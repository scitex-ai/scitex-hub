#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module Maker URL configuration."""

from __future__ import annotations

from django.urls import path

app_name = "modulemaker"

from . import views

urlpatterns = [
    # Pages
    path("", views.my_modules, name="my_modules"),
    path("new/", views.editor, name="editor_new"),
    path("<slug:slug>/edit/", views.editor, name="editor"),
    # API — CRUD
    path("api/create/", views.api_create_module, name="api_create"),
    path("api/<slug:slug>/update/", views.api_update_module, name="api_update"),
    path("api/<slug:slug>/run/", views.api_run_module, name="api_run"),
    path("api/<slug:slug>/delete/", views.api_delete_module, name="api_delete"),
    # API — Git import
    path("api/import-github/", views.api_import_from_github, name="api_import_github"),
    path("api/<slug:slug>/sync/", views.api_sync_from_github, name="api_sync"),
]


# EOF
