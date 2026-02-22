#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module Maker app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class ModulemakerAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.modulemaker_app"
    verbose_name = "Module Maker"


# EOF
