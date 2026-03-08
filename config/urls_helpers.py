# -*- coding: utf-8 -*-
# Timestamp: 2026-03-09
# File: /home/ywatanabe/proj/scitex-cloud/config/urls_helpers.py
"""
Helper functions extracted from config/urls.py to reduce file size.
"""

from __future__ import annotations

from django.conf import settings


def get_reserved_paths():
    """
    Dynamically generate list of reserved URL prefixes.
    Returns list of paths that cannot be used as usernames.
    """
    from pathlib import Path

    reserved = set()

    # 1. Auto-discover app URL prefixes
    apps_dir = Path(settings.BASE_DIR) / "apps"
    if apps_dir.exists():
        for app_dir in sorted(apps_dir.iterdir()):
            if app_dir.is_dir() and not app_dir.name.startswith("_"):
                urls_file = app_dir / "urls.py"
                if urls_file.exists():
                    url_prefix = app_dir.name.replace("_app", "")
                    reserved.add(url_prefix)

    # 2. Static system paths
    reserved.update(
        [
            "admin",
            "api",
            "new",
            "static",
            "media",
            "accounts",
            "auth",
            "files",
            "healthz",
            "favicon.ico",
            "robots.txt",
            "sitemap.xml",
        ]
    )

    # 3. Common reserved words (user-facing pages)
    reserved.update(
        [
            "about",
            "help",
            "support",
            "contact",
            "terms",
            "privacy",
            "settings",
            "dashboard",
            "profile",
            "account",
            "login",
            "logout",
            "signup",
            "register",
            "reset",
            "verify",
            "confirm",
            "explore",
            "current-project",
            "trending",
            "discover",
            "social",
        ]
    )

    # 4. Development/debug paths
    if settings.DEBUG:
        reserved.update(["__reload__", "__debug__"])

    return sorted(list(reserved))


# Generate reserved paths at module level
RESERVED_PATHS = get_reserved_paths()


def dev_module_view(request, rest):
    """Serve dev-installed app modules via workspace shell."""
    from apps.workspace_app.views import workspace_shell

    return workspace_shell(request, module=f"dev__{rest}")


# EOF
