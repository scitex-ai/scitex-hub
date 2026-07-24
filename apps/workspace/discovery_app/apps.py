#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Discovery App — public repository and user discovery workspace module."""

from django.apps import AppConfig


class DiscoveryAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace.discovery_app"
    label = "discovery_app"
    verbose_name = "Explore"
