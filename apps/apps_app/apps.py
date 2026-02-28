#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apps (formerly Marketplace) app configuration."""

from django.apps import AppConfig


class AppsAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.apps_app"
    verbose_name = "Apps"


# EOF
