# -*- coding: utf-8 -*-
# File: apps/infra/mcp_api/apps.py
"""Django app config for MCP REST API bridge."""

from django.apps import AppConfig


class McpApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.infra.mcp_api"
    verbose_name = "MCP REST API"

    def ready(self):
        """Build URL patterns from discovered MCP tools at startup."""
        from . import urls as urls_module

        urls_module._build_urlpatterns()


# EOF
