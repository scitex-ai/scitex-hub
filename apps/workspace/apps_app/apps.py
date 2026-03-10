#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apps (formerly Marketplace) app configuration."""

from django.apps import AppConfig


class AppsAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace.apps_app"
    verbose_name = "Apps"

    def ready(self):
        """Load approved user apps and dev apps into workspace registry on startup."""
        try:
            from .services.app_loader import load_approved_apps

            load_approved_apps()
        except Exception:
            import logging

            logging.getLogger(__name__).debug(
                "[apps_app] Skipped loading approved apps (likely during migration)"
            )

        # Load dev preview apps if configured
        try:
            from django.conf import settings

            dev_apps = getattr(settings, "DEV_APPS", [])
            if dev_apps:
                from .services.app_loader import load_dev_apps

                load_dev_apps(dev_apps)
        except Exception:
            pass


# EOF
