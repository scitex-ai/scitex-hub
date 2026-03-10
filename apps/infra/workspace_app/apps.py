#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-14 17:45:00 (ywatanabe)"
# File: ./apps/workspace_app/apps.py

from django.apps import AppConfig


class WorkspaceAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.infra.workspace_app"
    verbose_name = "Workspace Management"


# EOF
