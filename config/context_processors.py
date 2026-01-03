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
                # Check modification time of all key JS directories
                js_dirs = [
                    Path(settings.BASE_DIR) / 'apps/code_app/static/code_app/js',
                    Path(settings.BASE_DIR) / 'apps/vis_app/static/vis_app/js',
                    Path(settings.BASE_DIR) / 'apps/writer_app/static/writer_app/js',
                    Path(settings.BASE_DIR) / 'static/shared/js',
                ]
                max_mtime = 0
                for js_dir in js_dirs:
                    if js_dir.exists():
                        for js_file in js_dir.rglob('*.js'):
                            mtime = js_file.stat().st_mtime
                            if mtime > max_mtime:
                                max_mtime = mtime
                _cached_build_id = str(int(max_mtime)) if max_mtime else str(int(current_time))
            except Exception:
                _cached_build_id = str(int(current_time))

            _last_check_time = current_time

        build_id = _cached_build_id or str(int(current_time))
    else:
        # In production, use a fixed version from settings or environment
        build_id = getattr(settings, 'BUILD_ID', os.environ.get('BUILD_ID', '1.0.0'))

    return {
        'build_id': build_id
    }


def debug_mode(request):
    """
    Always expose DEBUG setting to templates.
    Unlike django.template.context_processors.debug, this doesn't check INTERNAL_IPS.
    """
    return {
        'DEBUG': settings.DEBUG
    }


def scitex_version(request):
    """
    Expose SciTeX Cloud version to all templates.
    Single source of truth from settings.SCITEX_CLOUD_VERSION
    """
    return {
        'SCITEX_CLOUD_VERSION': getattr(settings, 'SCITEX_CLOUD_VERSION', '0.0.0')
    }


def google_analytics(request):
    """
    Expose Google Analytics Measurement ID to templates.
    Only sends tracking data if GOOGLE_ANALYTICS_ID is configured.
    """
    return {
        'GOOGLE_ANALYTICS_ID': getattr(settings, 'GOOGLE_ANALYTICS_ID', '')
    }
