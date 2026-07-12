# -*- coding: utf-8 -*-
# File: config/settings/settings_shared.py
"""
Django settings for SciTeX Hub project.
Base settings shared across all environments.
Sub-modules: settings_celery, settings_logging, settings_auth,
settings_integrations, settings_commerce
"""

import os
from pathlib import Path

import scitex as stx

from config import branding
from config._env import (
    getenv_with_legacy_alias as _getenv_alias,
)
from config._env import (
    require_env_with_legacy_alias as _require_env_alias,
)


# ---------------------------------------
# Functions
# ---------------------------------------
def require_env(var_name: str) -> str:
    """Get required environment variable or raise clear error.

    Honors the legacy ``SCITEX_CLOUD_*`` alias of ``SCITEX_HUB_*`` (ADR-0001):
    if the canonical name is unset but the deprecated alias is set, the alias
    value is returned and a ``DeprecationWarning`` is emitted (no silent
    fallback). Strictly one-direction (HUB canonical, CLOUD legacy).
    """
    return _require_env_alias(var_name)


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
# Environment identity
# ---------------------------------------
# Drives the tab title marker AND the favicon colour, so an operator can tell
# prod / staging / dev apart from the browser tab alone.
#
# Declared here so there is ALWAYS a value; each concrete settings module
# (settings_dev / settings_staging / settings_prod) then OVERRIDES it with its
# literal environment -- that override, not this env-var default, is the
# source of truth. `normalize_env` raises on an unknown value, so a typo fails
# fast at boot instead of silently serving the wrong environment's favicon.
SCITEX_ENV = branding.normalize_env(os.environ.get("SCITEX_HUB_ENV", "development"))

# The hub always renders apps EMBEDDED. A standalone SciTeX app (e.g.
# `scitex-writer gui` on its own port) sets this to branding.MODE_STANDALONE
# so its tab reads "Writer — SciTeX (standalone)" instead of "Writer — SciTeX".
SCITEX_APP_MODE = branding.MODE_HUB

# ---------------------------------------
# Paths
# ---------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_URLCONF = "config.urls"
# NOTE: LOG_DIR is deliberately NOT computed here. It is owned by
# settings_logging.py (the module that actually builds the
# RotatingFileHandlers) and reaches this module's namespace via
# `from .settings_logging import *` below. A duplicate computation used
# to live here too; it was dead code (silently overwritten by that
# import) that also created an unused GITIGNORED/logs directory on every
# boot. Removed together with the GITIGNORED/logs fallback itself -- see
# incident hub-prod-outage-celery-log-permission (2026-07-09/10).

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
SCITEX_HUB_VERSION = _get_version()
SCITEX_HUB_VISITOR_POOL_SIZE = int(
    _getenv_alias("SCITEX_HUB_VISITOR_POOL_SIZE", "4") or "4"
)
UMAMI_WEBSITE_ID = _getenv_alias("SCITEX_HUB_UMAMI_WEBSITE_ID", "")
UMAMI_SCRIPT_URL = _getenv_alias(
    "SCITEX_HUB_UMAMI_SCRIPT_URL", "https://cloud.umami.is/script.js"
)

# ---------------------------------------
# Security
# ---------------------------------------
# Honors SCITEX_CLOUD_DJANGO_SECRET_KEY as a deprecated alias (ADR-0001).
SECRET_KEY = _getenv_alias("SCITEX_HUB_DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SCITEX_HUB_DJANGO_SECRET_KEY must be set in environment")

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
    "oauth2_provider",
]

# Required: scitex_ui (available on PyPI as scitex-ui)
THIRD_PARTY_APPS.append("scitex_ui")

# Optional: figrecipe editor (static assets served via AppDirectoriesFinder)
try:
    import figrecipe  # noqa: F401

    THIRD_PARTY_APPS.append("figrecipe._django")
except ImportError:
    pass

# Optional: upstream scitex-writer app (contract-compliant _django app;
# URL-mounted under /writer/ in config/urls.py). The explicit AppConfig
# path is required: writer's apps.py holds two AppConfig candidates (the
# imported ScitexAppConfig base + WriterEditorConfig, no default=True),
# so a bare module entry falls back to label "_django" and collides with
# figrecipe._django's identical fallback.
try:
    import scitex_writer  # noqa: F401

    THIRD_PARTY_APPS.append("scitex_writer._django.apps.WriterEditorConfig")
except ImportError:
    pass

# Optional: upstream scitex-storage app (contract-compliant _django app;
# URL-mounted under /storage/ in config/urls.py). StorageConfig sets
# default=True and a unique label ("scitex_storage_django"), so the mount
# is collision-free; the explicit AppConfig path mirrors the writer/todo
# entries above.
#
# Gate on the _django SUBMODULE (not just the top-level package): the
# AppConfig we append lives in scitex_storage._django.apps, so a
# scitex_storage installed WITHOUT its _django app (an older published
# wheel, or a checkout from before its _django app merged) must skip
# cleanly here rather than crash Django app-loading with
# "ModuleNotFoundError: No module named 'scitex_storage._django'".
try:
    import scitex_storage._django  # noqa: F401

    THIRD_PARTY_APPS.append("scitex_storage._django.apps.StorageConfig")
except ImportError:
    pass

# Optional: upstream scitex-todo board app (contract-compliant _django app;
# URL-mounted under /todo/ in config/urls.py). The explicit AppConfig
# path mirrors the writer entry above: todo's apps.py holds two AppConfig
# candidates (the imported ScitexAppConfig base + ScitexTodoConfig, no
# default=True), so a bare module entry falls back to label "_django"
# and collides with figrecipe._django's identical fallback.
try:
    import scitex_todo  # noqa: F401

    THIRD_PARTY_APPS.append("scitex_todo._django.apps.ScitexTodoConfig")

    # Tenancy: the board's service layer (scitex_todo._django.services)
    # unions host-side per-project lanes (default glob
    # ~/proj/*/.scitex/todo/tasks.yaml) into every board load. On the hub
    # each request must see ONLY the requesting user's workspace store
    # (injected by apps.workspace.todo_app.middleware), so lane discovery
    # is explicitly disabled — an empty glob list is the documented
    # opt-out seam in that module.
    os.environ["SCITEX_TODO_LANE_GLOBS"] = ""
except ImportError:
    pass

LOCAL_APPS = discover_local_apps()
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Mirrors config.context_processors.scitex_env's alias normalization.
# Duplicated (not imported) because that module is only safe to import
# once Django app-loading has finished; settings modules must not
# depend on it. scitex-ui>=0.6.1 is required — 0.6.0 never shipped
# middleware.py (merged after that release was cut), and anything
# older than 0.6.1 is sync-only and deadlocks daphne under ASGI (see
# scitex-ui PR #59).
_scitex_hub_env = os.environ.get("SCITEX_HUB_ENV", "development").lower()
if _scitex_hub_env in ("dev",):
    _scitex_hub_env = "development"
elif _scitex_hub_env in ("stag",):
    _scitex_hub_env = "staging"
elif _scitex_hub_env in ("prod",):
    _scitex_hub_env = "production"
SCITEX_UI_ELEMENT_INSPECTOR = _scitex_hub_env in ("development", "staging")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # i18n rails (F: tokushoho/commerce pages). Locale resolution must sit
    # after SessionMiddleware and before CommonMiddleware per Django docs.
    # Scope decision: only legal/landing surfaces are authored in Japanese
    # for now — the app interior stays untranslated.
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Resolve Authorization: Bearer <jwt> → request.user for plain Django
    # views. Browser cookie-sessions short-circuit before this runs
    # (request.user already authenticated), so the middleware is a pure
    # addition that opens the JWT door to existing endpoints without
    # touching any view. See apps/infra/accounts_app/middleware.py.
    "apps.infra.accounts_app.middleware.JWTBearerToSessionMiddleware",
    "apps.infra.project_app.middleware.OnSiteAuthMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.infra.project_app.middleware.VisitorAutoLoginMiddleware",
    "apps.infra.project_app.middleware.VisitorExpirationMiddleware",
    "apps.infra.project_app.middleware.VisitorAppRedirectMiddleware",
    # Default-deny site-wide write guard for the shared readonly-visitor
    # role (card hub-visitor-slot-isolation-audit — closes the exact gap
    # that produced the field-found "Plaque" leak: per-view opt-in guards
    # had missed project creation entirely). Must run AFTER
    # VisitorAutoLoginMiddleware so request.user/session-role is final.
    # Per-view guards (file_save.py, todo_app middleware below) still
    # apply first for their richer error copy; this is the safety net.
    "apps.infra.project_app.middleware_readonly_write_guard.ReadonlyVisitorWriteGuardMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.infra.project_app.middleware.GuestSessionMiddleware",
    # Scope the mounted scitex-todo board (/todo/) to the requesting
    # user's workspace store + enforce the phase-1 read-only gate. Must
    # run AFTER Authentication + VisitorAutoLogin so request.user is
    # final; no-ops in one prefix check for every other path (and when
    # the scitex_todo package is not installed).
    "apps.workspace.todo_app.middleware.TodoBoardTenancyMiddleware",
    # Injects the Alt+I element inspector into HTML responses when
    # SCITEX_UI_ELEMENT_INSPECTOR is on (see above). Async-capable as
    # of scitex-ui 0.6.1 — do not downgrade below that pin.
    "scitex_ui.middleware.ElementInspectorMiddleware",
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
        "NAME": BASE_DIR / "data" / "db" / "sqlite" / "scitex_hub.db",
    }
}

# ---------------------------------------
# Cache + Sessions
# ---------------------------------------
REDIS_URL = _getenv_alias("SCITEX_HUB_REDIS_URL", "redis://127.0.0.1:6379/1")

try:
    import redis as _redis

    # Short, explicit timeouts so an unreachable / unanswered Redis fails
    # fast and we fall back to local cache, instead of blocking settings
    # import (and therefore django.setup()) on a hanging TCP connect — e.g.
    # under WSL2 where a closed port may hang rather than refuse.
    _r = _redis.from_url(REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
    _r.ping()
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "scitex_hub",
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

    _redis_url2 = _getenv_alias("SCITEX_HUB_REDIS_URL", "redis://127.0.0.1:6379/2")
    # Same fast-fail timeouts as the cache probe above — never block
    # settings import on an unreachable Redis.
    _redis2.from_url(_redis_url2, socket_connect_timeout=0.5, socket_timeout=0.5).ping()
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

# i18n rails — English default, Japanese for legal/landing pages
# (特定商取引法に基づく表記 etc.). Message catalogs live in locale/;
# regenerate with:
#   python manage.py makemessages -l ja
#   python manage.py compilemessages
LANGUAGES = [
    ("en", "English"),
    ("ja", "日本語"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = _getenv_alias("SCITEX_HUB_EMAIL_BACKEND")
EMAIL_HOST = _getenv_alias("SCITEX_HUB_EMAIL_HOST")
EMAIL_PORT = int(_getenv_alias("SCITEX_HUB_EMAIL_PORT", "587") or "587")
EMAIL_USE_TLS = (
    _getenv_alias("SCITEX_HUB_EMAIL_USE_TLS", "True") or "True"
).lower() == "true"
EMAIL_HOST_USER = _getenv_alias("SCITEX_HUB_EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = _getenv_alias("SCITEX_HUB_EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER
SITE_URL = _getenv_alias("SCITEX_HUB_SITE_URL", "http://127.0.0.1:8000")

# Campaign Chat Mode
SCITEX_HUB_CAMPAIGN_ANTHROPIC_API_KEY = _getenv_alias(
    "SCITEX_HUB_CAMPAIGN_ANTHROPIC_API_KEY", ""
)
SCITEX_HUB_CAMPAIGN_MODEL = _getenv_alias(
    "SCITEX_HUB_CAMPAIGN_MODEL", "claude-haiku-4-5-20251001"
)
SCITEX_HUB_CAMPAIGN_DAILY_LIMIT = _getenv_alias("SCITEX_HUB_CAMPAIGN_DAILY_LIMIT", "10")

# ---------------------------------------
# Sub-module imports (celery, logging, auth, integrations)
# ---------------------------------------
from .settings_auth import *  # noqa: E402, F401, F403
from .settings_celery import *  # noqa: E402, F401, F403
from .settings_commerce import *  # noqa: E402, F401, F403
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
