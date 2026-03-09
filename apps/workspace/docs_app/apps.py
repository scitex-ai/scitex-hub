#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/docs_app/apps.py

from django.apps import AppConfig


class DocsAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace.docs_app"
    verbose_name = "Docs"

    def ready(self):
        from apps.workspace.docs_app.views import register_module_docs

        register_module_docs()
