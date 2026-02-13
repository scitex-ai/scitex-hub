#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context processors for adding global template variables.
"""

import os
from pathlib import Path

from django.conf import settings

# Cache the build_id to avoid repeated file system calls
_cached_build_id = None
_last_check_time = 0


def cache_buster(request):
    """
    Add a cache-busting parameter for static files in development.
    In production, use proper static file versioning.

    In development, this checks the modification time of JS directories
    and updates when they change.
    """
    global _cached_build_id, _last_check_time

    if settings.DEBUG:
        import time

        current_time = time.time()

        # Check files every 2 seconds to avoid excessive file system calls
        if current_time - _last_check_time > 2:
            try:
                # Check modification time of key JS and CSS directories
                static_dirs = [
                    Path(settings.BASE_DIR) / "apps/console_app/static/console_app/js",
                    Path(settings.BASE_DIR) / "apps/vis_app/static/vis_app/js",
                    Path(settings.BASE_DIR) / "apps/writer_app/static/writer_app/js",
                    Path(settings.BASE_DIR) / "static/shared/js",
                    Path(settings.BASE_DIR) / "static/shared/css",
                    Path(settings.BASE_DIR) / "apps/writer_app/static/writer_app/css",
                    Path(settings.BASE_DIR) / "apps/scholar_app/static/scholar_app/css",
                    Path(settings.BASE_DIR) / "apps/console_app/static/console_app/css",
                    Path(settings.BASE_DIR) / "apps/vis_app/static/vis_app/css",
                    Path(settings.BASE_DIR) / "apps/public_app/static/public_app/css",
                ]
                max_mtime = 0
                for static_dir in static_dirs:
                    if static_dir.exists():
                        for static_file in static_dir.rglob("*"):
                            if static_file.suffix in (".js", ".css"):
                                mtime = static_file.stat().st_mtime
                                if mtime > max_mtime:
                                    max_mtime = mtime
                _cached_build_id = (
                    str(int(max_mtime)) if max_mtime else str(int(current_time))
                )
            except Exception:
                _cached_build_id = str(int(current_time))

            _last_check_time = current_time

        build_id = _cached_build_id or str(int(current_time))
    else:
        # In production, use a fixed version from settings or environment
        build_id = getattr(settings, "BUILD_ID", os.environ.get("BUILD_ID", "1.0.0"))

    return {"build_id": build_id}


def debug_mode(request):
    """
    Always expose DEBUG setting to templates.
    Unlike django.template.context_processors.debug, this doesn't check INTERNAL_IPS.
    """
    return {"DEBUG": settings.DEBUG}


def scitex_version(request):
    """
    Expose SciTeX Cloud version to all templates.
    Single source of truth: settings.SCITEX_CLOUD_VERSION
    """
    return {"SCITEX_CLOUD_VERSION": get_scitex_cloud_version()}


def get_scitex_cloud_version():
    """
    Get version from Django settings (single source of truth).
    settings.SCITEX_CLOUD_VERSION is the scitex-cloud web app version,
    separate from pyproject.toml which is for the pypi package.
    """
    return getattr(settings, "SCITEX_CLOUD_VERSION", "0.0.0")


def umami_analytics(request):
    """
    Expose Umami Analytics configuration to templates.
    Umami is privacy-focused and does not use cookies.
    """
    return {
        "UMAMI_WEBSITE_ID": getattr(settings, "UMAMI_WEBSITE_ID", ""),
        "UMAMI_SCRIPT_URL": getattr(
            settings, "UMAMI_SCRIPT_URL", "https://cloud.umami.is/script.js"
        ),
        "UMAMI_DOMAINS": os.environ.get("SCITEX_CLOUD_UMAMI_DOMAINS", ""),
    }


def site_branding(request):
    """
    Expose site branding constants to all templates.
    Single source of truth: config/branding.py
    """
    from config import branding

    return {
        "SITE_NAME": branding.SITE_NAME,
        "SITE_TAGLINE": branding.SITE_TAGLINE,
        "SITE_DESCRIPTION": branding.SITE_DESCRIPTION,
        "META_DESCRIPTION_DEFAULT": branding.META_DESCRIPTION_DEFAULT,
        "OG_TITLE": branding.OG_TITLE,
        "OG_DESCRIPTION": branding.OG_DESCRIPTION,
    }


def scitex_env(request):
    """
    Expose SCITEX_CLOUD_ENV to templates for environment-specific rendering.
    Values: 'development', 'staging', 'production'
    """
    env = os.environ.get("SCITEX_CLOUD_ENV", "development").lower()
    # Normalize aliases
    if env in ("dev",):
        env = "development"
    elif env in ("stag",):
        env = "staging"
    elif env in ("prod",):
        env = "production"
    return {
        "SCITEX_ENV": env,
        "IS_STAGING": env == "staging",
        "IS_PRODUCTION": env == "production",
    }
