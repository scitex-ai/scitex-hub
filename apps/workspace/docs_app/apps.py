#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/docs_app/apps.py

from django.apps import AppConfig


class DocsAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace.docs_app"
    verbose_name = "Docs"

    def ready(self):
        from apps.workspace.docs_app._sphinx import register_sphinx_packages
        from apps.workspace.docs_app.views import (
            _PAGES_BY_SLUG,
            DOCS_PAGES,
            register_module_docs,
        )

        register_module_docs()
        register_sphinx_packages(DOCS_PAGES, _PAGES_BY_SLUG)
