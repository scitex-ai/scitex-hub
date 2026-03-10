#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App Maker app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class AppmakerAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.infra.appmaker_app"
    verbose_name = "App Maker"


# EOF
