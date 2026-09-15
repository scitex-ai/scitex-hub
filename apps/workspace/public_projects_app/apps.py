#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public Projects App — public repository and user public projects workspace module."""

from django.apps import AppConfig


class PublicProjectsAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace.public_projects_app"
    label = "public_projects_app"
    verbose_name = "Public Projects"
