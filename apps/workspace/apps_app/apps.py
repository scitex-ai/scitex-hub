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

        from .services.plugin_apps import register_plugin_modules

        register_plugin_modules()

        # SDK UI JS-catalog fallback (fix-forward #1065): the SDK creator
        # wizard's shell catalogues scitex_sdk.ui, which stays out of
        # INSTALLED_APPS (duplicate scitex_ui label) — patch the tag's
        # lookup so it serves the package locale dir instead of raising.
        try:
            from .services.sdk_i18n_fallback import install as _install_sdk_i18n

            _install_sdk_i18n()
        except Exception:
            import logging

            logging.getLogger(__name__).debug(
                "[apps_app] SDK i18n fallback not installed"
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
