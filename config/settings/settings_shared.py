# -*- coding: utf-8 -*-
# File: config/settings/settings_shared.py
"""
Django settings for SciTeX Cloud project.
Base settings shared across all environments.
Sub-modules: settings_celery, settings_logging, settings_auth, settings_integrations
"""

import os
from pathlib import Path

import scitex as stx


# ---------------------------------------
# Functions
# ---------------------------------------
def require_env(var_name: str) -> str:
    """Get required environment variable or raise clear error."""
    value = os.environ.get(var_name)
    if value is None:
        raise EnvironmentError(
            f"Required environment variable '{var_name}' is not set. "
            f"Check deployment/docker/envs/.env.{{ENV}} file."
        )
    return value


def discover_local_apps():
    """Discover all Django apps in apps/, apps/infra/, and apps/workspace/."""
    apps_path = BASE_DIR / "apps"
    local_apps = []
    if not apps_path.exists():
        return local_apps

    # Scan subdirectory groups first
    for group in ("infra", "workspace"):
        group_path = apps_path / group
        if group_path.exists():
            for item in sorted(group_path.iterdir()):
                if item.is_dir() and not item.name.startswith("_"):
                    if (item / "apps.py").exists():
                        local_apps.append(f"apps.{group}.{item.name}")

    # Scan flat apps/ level (legacy fallback, future additions)
    for item in sorted(apps_path.iterdir()):
        if item.is_dir() and not item.name.startswith("_"):
            if item.name in ("infra", "workspace", "legacy"):
                continue
            if (item / "apps.py").exists():
                local_apps.append(f"apps.{item.name}")

    return local_apps


def _get_version():
    """Read version from pyproject.toml (single source of truth)."""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    pyproject = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
    if pyproject.exists():
        with open(pyproject, "rb") as f:
            return tomllib.load(f).get("project", {}).get("version", "unknown")
    return "unknown"


# ---------------------------------------
# Paths
# ---------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_URLCONF = "config.urls"
LOG_DIR = BASE_DIR / "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static", BASE_DIR / ".jsbuild"]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "apps.workspace.apps_app.finders.DevAppStaticFinder",
]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Vite dev server port for dev app TypeScript (container Vite)
VITE_DEV_APP_PORT = 5174

# Allow larger request bodies for base64 image attachments in AI chat (default 2.5MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100 MB

LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# ---------------------------------------
# Metadata
# ---------------------------------------
SCITEX_CLOUD_VERSION = _get_version()
SCITEX_CLOUD_VISITOR_POOL_SIZE = int(
    os.environ.get("SCITEX_CLOUD_VISITOR_POOL_SIZE", 4)
)
UMAMI_WEBSITE_ID = os.environ.get("SCITEX_CLOUD_UMAMI_WEBSITE_ID", "")
UMAMI_SCRIPT_URL = os.environ.get(
    "SCITEX_CLOUD_UMAMI_SCRIPT_URL", "https://cloud.umami.is/script.js"
)

# ---------------------------------------
# Security
# ---------------------------------------
SECRET_KEY = os.getenv("SCITEX_CLOUD_DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SCITEX_CLOUD_DJANGO_SECRET_KEY must be set in environment")

# ---------------------------------------
# Applications
# ---------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "channels",
    "django_celery_results",
    "django_celery_beat",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.orcid",
    "scitex_ui",
]

LOCAL_APPS = discover_local_apps()
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.infra.project_app.middleware.OnSiteAuthMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.infra.project_app.middleware.VisitorAutoLoginMiddleware",
    "apps.infra.project_app.middleware.VisitorExpirationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.infra.project_app.middleware.GuestSessionMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------
# Templates
# ---------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.infra.project_app.context_processors.version_context",
                "apps.infra.project_app.context_processors.project_context",
                "apps.infra.project_app.context_processors.visitor_expiration_context",
                "config.context_processors.cache_buster",
                "config.context_processors.debug_mode",
                "config.context_processors.scitex_version",
                "config.context_processors.umami_analytics",
                "config.context_processors.site_branding",
                "config.context_processors.scitex_env",
                "apps.infra.workspace_app.context_processors.workspace_context",
            ],
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
                "apps.workspace.apps_app.template_loader.UserAppTemplateLoader",
            ],
        },
    },
]

# ---------------------------------------
# Database (override in environment settings)
# ---------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "data" / "db" / "sqlite" / "scitex_cloud.db",
    }
}

# ---------------------------------------
# Cache + Sessions
# ---------------------------------------
REDIS_URL = os.getenv("SCITEX_CLOUD_REDIS_URL", "redis://127.0.0.1:6379/1")

try:
    import redis as _redis

    _r = _redis.from_url(REDIS_URL)
    _r.ping()
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "scitex_cloud",
            "TIMEOUT": 3600,
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
except (ImportError, Exception):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "cache_table",
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

SESSION_COOKIE_AGE = 86400

# ---------------------------------------
# Channel Layers
# ---------------------------------------
try:
    import redis as _redis2

    _redis_url2 = os.getenv("SCITEX_CLOUD_REDIS_URL", "redis://127.0.0.1:6379/2")
    _redis2.from_url(_redis_url2).ping()
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [_redis_url2]},
        },
    }
except (ImportError, Exception):
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# ---------------------------------------
# Password validation / i18n / misc
# ---------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = os.getenv("SCITEX_CLOUD_EMAIL_BACKEND")
EMAIL_HOST = os.getenv("SCITEX_CLOUD_EMAIL_HOST")
EMAIL_PORT = int(os.getenv("SCITEX_CLOUD_EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("SCITEX_CLOUD_EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.getenv("SCITEX_CLOUD_EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("SCITEX_CLOUD_EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER
SITE_URL = os.getenv("SCITEX_CLOUD_SITE_URL", "http://127.0.0.1:8000")

# Campaign Chat Mode
SCITEX_CLOUD_CAMPAIGN_ANTHROPIC_API_KEY = os.getenv(
    "SCITEX_CLOUD_CAMPAIGN_ANTHROPIC_API_KEY", ""
)
SCITEX_CLOUD_CAMPAIGN_MODEL = os.getenv(
    "SCITEX_CLOUD_CAMPAIGN_MODEL", "claude-haiku-4-5-20251001"
)
SCITEX_CLOUD_CAMPAIGN_DAILY_LIMIT = os.getenv("SCITEX_CLOUD_CAMPAIGN_DAILY_LIMIT", "10")

# ---------------------------------------
# Sub-module imports (celery, logging, auth, integrations)
# ---------------------------------------
from .settings_auth import *  # noqa: E402, F401, F403
from .settings_celery import *  # noqa: E402, F401, F403
from .settings_integrations import *  # noqa: E402, F401, F403
from .settings_logging import *  # noqa: E402, F401, F403

# SIMPLE_JWT requires SECRET_KEY defined above
SIMPLE_JWT = get_simple_jwt_settings(SECRET_KEY)  # noqa: F821


@stx.session
def main(CONFIG=stx.session.INJECTED):
    """Settings module — not meant to be executed directly."""
    return 0


if __name__ == "__main__":
    main()

# EOF
