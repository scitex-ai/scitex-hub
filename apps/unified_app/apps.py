#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from django.apps import AppConfig


class UnifiedConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.unified_app"
    label = "unified_app"
    verbose_name = "Unified Workspace"


# EOF
