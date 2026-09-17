"""SQLite-only settings for request-level review tests.

This module is not used by a deployed environment. It lets file-backed views
exercise the real URL/template stack without requiring the development
PostgreSQL service.
"""

from .settings_shared import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
