#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Marketplace app configuration."""

from django.apps import AppConfig


class MarketplaceAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.marketplace_app"
    verbose_name = "Marketplace"


# EOF
