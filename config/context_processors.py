#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context processors for adding global template variables.
"""

import os
from pathlib import Path

from django.conf import settings

from config import branding

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
                    Path(settings.BASE_DIR)
                    / "apps/workspace/console_app/static/console_app/js",
                    Path(settings.BASE_DIR)
                    / "apps/workspace/figrecipe_app/static/figrecipe_app/ts",
                    Path(settings.BASE_DIR)
                    / "apps/workspace/writer_app/static/writer_app/js",
                    Path(settings.BASE_DIR) / "static/shared/js",
                    Path(settings.BASE_DIR) / "static/shared/css",
                    Path(settings.BASE_DIR)
                    / "apps/workspace/writer_app/static/writer_app/css",
                    Path(settings.BASE_DIR)
                    / "apps/workspace/scholar_app/static/scholar_app/css",
                    Path(settings.BASE_DIR)
                    / "apps/workspace/console_app/static/console_app/css",
                    Path(settings.BASE_DIR)
                    / "apps/infra/public_app/static/public_app/css",
                    Path(settings.BASE_DIR)
                    / "apps/workspace/docs_app/static/docs_app/css",
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
        # In production, derive build_id from .build-timestamp file, then
        # SCITEX_HUB_BUILD_ID env var, falling back to timestamp.
        build_id = ""
        try:
            ts_file = Path(settings.STATIC_ROOT) / "vite" / ".build-timestamp"
            if ts_file.exists():
                build_id = ts_file.read_text().strip()[:10]
        except Exception:
            pass
        if not build_id:
            build_id = os.environ.get("SCITEX_HUB_BUILD_ID", "")
        if not build_id:
            import time

            build_id = str(int(time.time()))

    return {"build_id": build_id}


def debug_mode(request):
    """
    Always expose DEBUG setting to templates.
    Unlike django.template.context_processors.debug, this doesn't check INTERNAL_IPS.
    """
    return {"DEBUG": settings.DEBUG}


def scitex_version(request):
    """
    Expose SciTeX Hub version to all templates.
    Single source of truth: settings.SCITEX_HUB_VERSION
    """
    return {"SCITEX_HUB_VERSION": get_scitex_hub_version()}


def get_scitex_hub_version():
    """
    Get version from Django settings (single source of truth).
    settings.SCITEX_HUB_VERSION is the scitex-hub web app version,
    separate from pyproject.toml which is for the pypi package.
    """
    return getattr(settings, "SCITEX_HUB_VERSION", "0.0.0")


def umami_analytics(request):
    """
    Expose Umami Analytics configuration to templates.
    Umami is privacy-focused and does not use cookies.
    Respects user's analytics_opt_out preference.
    """
    # Check if user has opted out of analytics
    opted_out = False
    if hasattr(request, "user") and request.user.is_authenticated:
        try:
            opted_out = request.user.profile.analytics_opt_out
        except Exception:
            pass

    return {
        "UMAMI_WEBSITE_ID": (
            "" if opted_out else getattr(settings, "UMAMI_WEBSITE_ID", "")
        ),
        "UMAMI_SCRIPT_URL": getattr(
            settings, "UMAMI_SCRIPT_URL", "https://cloud.umami.is/script.js"
        ),
        "UMAMI_DOMAINS": os.environ.get("SCITEX_HUB_UMAMI_DOMAINS", ""),
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
        "SITE_TAGLINE_SECONDARY": branding.SITE_TAGLINE_SECONDARY,
        "SITE_DESCRIPTION": branding.SITE_DESCRIPTION,
        "META_DESCRIPTION_DEFAULT": branding.META_DESCRIPTION_DEFAULT,
        "OG_TITLE": branding.OG_TITLE,
        "OG_DESCRIPTION": branding.OG_DESCRIPTION,
        # Public contact addresses. Templates must use these rather than
        # hardcoding an address, so changing one is a single edit and cannot go
        # half-applied across pages. NOTE templates/500.html cannot use them —
        # Django's default handler500 renders without context processors, so a
        # {{ }} there would emit an empty mailto:. See config/branding.py.
        "CONTACT_EMAIL": branding.CONTACT_EMAIL,
        "LEGAL_EMAIL": branding.LEGAL_EMAIL,
        "PRIVACY_EMAIL": branding.PRIVACY_EMAIL,
        "RECRUIT_EMAIL": branding.RECRUIT_EMAIL,
        # branding.NOREPLY_EMAIL is deliberately NOT exported: it is a mail
        # SENDER, never something a page invites a reader to write to. Its one
        # use site (apps/infra/public_app/tasks/health.py) is Python and imports
        # the constant directly.
    }


def scitex_env(request):
    """
    Expose the deployment environment to templates.

    The environment is read from ``settings.SCITEX_ENV``, which each concrete
    settings module (settings_dev / settings_staging / settings_prod) declares
    literally. It is deliberately NOT re-derived from the SCITEX_HUB_ENV
    environment variable here: the settings module Django is actually running
    under IS the environment, and reading it twice from two sources is how the
    favicon and the deployment drift apart.

    ``SCITEX_FAVICON`` is the static-relative path of the environment's tab
    icon -- the same SciTeX brand mark in a per-environment colour, so prod /
    staging / dev are distinguishable from the tab icon alone.
    """
    env = branding.normalize_env(settings.SCITEX_ENV)
    return {
        "SCITEX_ENV": env,
        "IS_STAGING": env == branding.ENV_STAGING,
        "IS_PRODUCTION": env == branding.ENV_PRODUCTION,
        "SCITEX_FAVICON": branding.favicon_for_env(env),
        # "dev" / "staging" / "standalone", or None in hub production. Same
        # marker the tab title uses, so chrome and tab never disagree.
        "SCITEX_ENV_MARKER": branding.title_marker(env, settings.SCITEX_APP_MODE),
    }
