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

from ._optional_apps import optional_upstream_apps, with_plugin_apps


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

# Storage leaf asks the hub which directories belong to the requester.
SCITEX_STORAGE_VOLUMES_PROVIDER = "apps.workspace.storage_app.volumes.user_volumes"

# Project-scope apps (scitex-stats project-default mode, scitex-ui picker) ask the
# hub where an AUTHORIZED project's files live and whether this request may write.
# Request-aware: the class resolves the project through the same access-scoped lookup
# the picker lists from, and answers per request, not per process. It is NOT the
# picker itself — a provider entry carries display metadata, never a path.
SCITEX_PROJECT_STORAGE = "apps.infra.project_app.services.project_scope.HubProjectStorage"

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

# Static/media config (incl. the content-hashing storage backend) lives in
# settings_static.py — see the long note there on why the hashing is
# load-bearing, not cosmetic.
from .settings_static import *  # noqa: F401,F403,E402
from .settings_static import configure as _configure_static  # noqa: E402

globals().update(_configure_static(BASE_DIR))

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
UMAMI_WEBSITE_ID = _getenv_alias("SCITEX_HUB_UMAMI_WEBSITE_ID", "")
UMAMI_SCRIPT_URL = _getenv_alias(
    "SCITEX_HUB_UMAMI_SCRIPT_URL", "https://cloud.umami.is/script.js"
)

# ---------------------------------------
# Unix identity the WEB process serves as
# ---------------------------------------
# Declared HERE, once, because this identity is a property of the DEPLOYMENT,
# not of whichever service happens to use it. CI runners may not have the
# production account, so every caller must treat an unresolvable value as an
# explicit deployment error.
#
# Accepted forms: a user NAME (`scitex`), a numeric uid (`1000`), or an explicit
# `<user>:<group>` pair of either (`scitex:scitex`, `1000:1000`). A name is
# resolved through pwd/grp and an unresolvable value fails loudly. There is no
# fallback to "whoever happens to be running" because that may be root.
APP_UNIX_OWNER = _getenv_alias("SCITEX_HUB_APP_UNIX_OWNER", "scitex") or "scitex"

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

# Optional upstream SciTeX apps (figrecipe / writer / storage / cards).
# Which of them are installed, and which AppConfig path each one needs,
# lives in _optional_apps.py — including the scitex-cards rename-window
# shim and the reason it exists. Extracted 2026-08-16.
THIRD_PARTY_APPS.extend(optional_upstream_apps())
# Plugin apps: `pip install <pkg>` with a `scitex.apps` entry point (scitex_app.plugins).
THIRD_PARTY_APPS = with_plugin_apps(THIRD_PARTY_APPS)

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

# Host service for leaf apps' project pickers (scitex_ui.project_scope).
SCITEX_PROJECT_PROVIDER = "apps.infra.project_app.services.project_scope.HubProjectProvider"
SCITEX_PROJECT_PROVIDER_URL = "api_project_scope"

# ── Internal-app release channel ────────────────────────────────────────
# Whether "internal"-visibility apps (Cards, Storage, todo, …) are released
# to EVERY authenticated user on this deployment — not just staff. Operator
# ruling (card hub-cards-internal-entitlement-20260913, 2026-09-13): internal
# is a release-channel property, not an admin-role property. Accounts allowed
# to log in to a development deployment are the SciTeX team, so the dev
# settings module forces this True; production keeps it False (internal apps
# hidden unless a deployment deliberately releases them). Staff always see
# internal apps regardless (see can_view_internal_app). Env-overridable so a
# specific deployment can opt in without a code change.
SCITEX_HUB_INTERNAL_APPS_RELEASED = (
    _getenv_alias("SCITEX_HUB_INTERNAL_APPS_RELEASED", "false") or "false"
).lower() in ("1", "true", "yes", "on")

# ── On-site agent auth (HMAC shared secret) ────────────────────────────
# Shared with the MCP client running inside the user's agent container
# (scitex_hub._mcp_tools.api.get_on_site_env injects the same value as
# SCITEX_HUB_ONSITE_SECRET). OnSiteAuthMiddleware verifies an HMAC over
# (username, timestamp) against it. Empty => on-site auth is DISABLED
# (fail closed); it is never a "trusted network" fallback, because the
# previous IP-based signal was client-forgeable (X-Forwarded-For).
ONSITE_AUTH_SECRET = os.environ.get("SCITEX_HUB_ONSITE_SECRET", "")

# The MIDDLEWARE stack (order-sensitive, commented per entry) lives in its own
# module; imported under the same name so env modules can extend it.
from .settings_middleware import MIDDLEWARE  # noqa: E402, F401

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
                "config.context_processors.cache_buster",
                "config.context_processors.debug_mode",
                "config.context_processors.scitex_version",
                "config.context_processors.umami_analytics",
                "config.context_processors.site_branding",
                "config.context_processors.scitex_env",
                "config.context_processors.writer_api_base",
                "config.context_processors.mounted_app_launcher",
                "config.context_processors.header_logo",
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
# PostgreSQL is the ONLY supported engine, per the 2026-08-29 fleet ruling
# that removed every embedded file-backed database from the ecosystem. There
# is deliberately no second branch here: an environment that cannot reach
# Postgres must fail loudly at connect time rather than silently degrade onto
# a local file whose contents nobody else can see.
#
# Every environment module (settings_dev / settings_staging / settings_prod)
# reassigns DATABASES, so this block is the base for a direct
# `config.settings.settings_shared` import only.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _getenv_alias("SCITEX_HUB_DB_NAME", "scitex_hub"),
        "USER": _getenv_alias("SCITEX_HUB_DB_USER", "scitex"),
        "PASSWORD": _getenv_alias("SCITEX_HUB_DB_PASSWORD", ""),
        "HOST": _getenv_alias("SCITEX_HUB_DB_HOST", "localhost"),
        "PORT": _getenv_alias("SCITEX_HUB_DB_PORT", "5432"),
        "ATOMIC_REQUESTS": False,
        "CONN_MAX_AGE": 600,
        "OPTIONS": {
            "connect_timeout": 10,
        },
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

# Recipients of the mail_admins logging handler (settings_logging). Defined
# HERE, once, rather than per environment: it lived only in settings_prod
# until 2026-08-15, which meant staging constructed the handler, passed every
# check a grep could make, and delivered to nobody because ADMINS was the
# empty default. require_debug_false already keeps this off dev machines, so
# the environment gate does not need a second, silent one.
ADMINS = [
    ("Admin", "admin@scitex.ai"),
    ("Yusuke Watanabe", "ywatanabe@scitex.ai"),
]
MANAGERS = ADMINS
SITE_URL = _getenv_alias("SCITEX_HUB_SITE_URL", "http://127.0.0.1:8000")

# Campaign Chat Mode
SCITEX_HUB_CAMPAIGN_ANTHROPIC_API_KEY = _getenv_alias(
    "SCITEX_HUB_CAMPAIGN_ANTHROPIC_API_KEY", ""
)
SCITEX_HUB_CAMPAIGN_MODEL = _getenv_alias(
    "SCITEX_HUB_CAMPAIGN_MODEL", "claude-haiku-4-5-20251001"
)
SCITEX_HUB_CAMPAIGN_DAILY_LIMIT = _getenv_alias("SCITEX_HUB_CAMPAIGN_DAILY_LIMIT", "10")

# SciTeX-funded Chat. Enabled is the operator kill switch: when false, the
# funded path cannot reserve quota or contact a provider. Provider/model/caps
# intentionally have no useful defaults; enabling an incomplete configuration
# fails closed in funded_chat.config rather than silently selecting a model.
SCITEX_FUNDED_CHAT_ENABLED = (
    _getenv_alias("SCITEX_FUNDED_CHAT_ENABLED", "false") or "false"
).lower() in ("1", "true", "yes", "on")
SCITEX_FUNDED_CHAT_PROVIDER = _getenv_alias("SCITEX_FUNDED_CHAT_PROVIDER", "")
SCITEX_FUNDED_CHAT_MODEL = _getenv_alias("SCITEX_FUNDED_CHAT_MODEL", "")
SCITEX_FUNDED_CHAT_API_KEY = _getenv_alias("SCITEX_FUNDED_CHAT_API_KEY", "")
SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD = _getenv_alias(
    "SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD", "0"
)
SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD = _getenv_alias(
    "SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD", "0"
)
SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD = _getenv_alias(
    "SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD", "0"
)
SCITEX_FUNDED_CHAT_REQUESTS_PER_MINUTE = int(
    _getenv_alias("SCITEX_FUNDED_CHAT_REQUESTS_PER_MINUTE", "3") or "3"
)
SCITEX_FUNDED_CHAT_MAX_TOKENS = int(
    _getenv_alias(
        "SCITEX_FUNDED_CHAT_MAX_TOKENS", "2048"
    )  # pragma: allowlist secret -- output-token count, not a credential
    or "2048"
)

# ---------------------------------------
# Sub-module imports (celery, logging, auth, integrations)
# ---------------------------------------
from .settings_auth import *  # noqa: E402, F401, F403
from .settings_celery import *  # noqa: E402, F401, F403
from .settings_commerce import *  # noqa: E402, F401, F403
from .settings_integrations import *  # noqa: E402, F401, F403
from .settings_logging import *  # noqa: E402, F401, F403

# SIMPLE_JWT requires SECRET_KEY defined above
SIMPLE_JWT = get_simple_jwt_settings(SECRET_KEY)  # noqa: F405


@stx.session
def main(CONFIG=stx.session.INJECTED):
    """Settings module — not meant to be executed directly."""
    return 0


if __name__ == "__main__":
    main()

# EOF
