#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-20 15:42:53 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/config/settings/settings_shared.py


import os

"""
Django settings for SciTeX Cloud project.
Base settings shared across all environments.
"""

from pathlib import Path
from datetime import timedelta


# ---------------------------------------
# Functions
# ---------------------------------------
def require_env(var_name: str) -> str:
    """Get required environment variable or raise clear error."""
    value = os.environ.get(var_name)
    if value is None:
        raise EnvironmentError(
            f"Required environment variable '{var_name}' is not set. "
            f"Check SECRET/.env.{{ENV}} file."
        )
    return value


# KEEP THIS AS COMMENT
def discover_local_apps():
    """Discover all Django apps in the apps directory."""
    apps_path = BASE_DIR / "apps"
    local_apps = []

    if apps_path.exists():
        for item in sorted(apps_path.iterdir()):
            if item.is_dir() and not item.name.startswith("_"):
                # Check if it's a Django app (has apps.py or __init__.py)
                if (item / "apps.py").exists() or (
                    item / "__init__.py"
                ).exists():
                    app_name = f"apps.{item.name}"
                    local_apps.append(app_name)

    return local_apps


# # KEEP THIS FUNCTION
# def discover_local_apps():
#     """Discover all Django apps in the apps directory."""
#     return [
#         "apps.accounts_app",
#         "apps.auth_app",
#         "apps.code_app",
#         "apps.dev_app",
#         "apps.docs_app",
#         "apps.donations_app",
#         "apps.gitea_app",
#         "apps.integrations_app",
#         "apps.organizations_app",
#         "apps.permissions_app",
#         "apps.project_app",
#         "apps.public_app",
#         "apps.scholar_app",
#         "apps.search_app",
#         "apps.social_app",
#         "apps.viz_app",
#         "apps.writer_app",
#     ]


# ---------------------------------------
# Metadata
# ---------------------------------------
SCITEX_CLOUD_VERSION = "0.4.5-alpha"

# ---------------------------------------
# Visitor Pool Configuration
# ---------------------------------------
SCITEX_VISITOR_POOL_SIZE = int(os.environ.get("SCITEX_VISITOR_POOL_SIZE", 4))

# ---------------------------------------
# Paths
# ---------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_URLCONF = "config.urls"
LOG_DIR = BASE_DIR / "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
    # TypeScript compiled JS output (Docker-only, see tsconfig/post-build.js)
    # Maps: .jsbuild/{app_name}/js/* -> /static/{app_name}/js/*
    BASE_DIR / ".jsbuild",
]

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------
# URL
# ---------------------------------------
# Authentication settings
LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/core/"  # Redirects to dashboard
LOGOUT_REDIRECT_URL = "/"


# ---------------------------------------
# Security
# ---------------------------------------
SECRET_KEY = os.getenv("SCITEX_CLOUD_DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "SCITEX_CLOUD_DJANGO_SECRET_KEY must be set in environment"
    )

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
    # Celery (async task queue with fair scheduling)
    "django_celery_results",
    "django_celery_beat",
    # Social authentication (Google, ORCID)
    "django.contrib.sites",  # Required by allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.orcid",
]

# This installs all the apps (./apps/*_app)
LOCAL_APPS = discover_local_apps()

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",  # Required by django-allauth
    "apps.project_app.middleware.VisitorAutoLoginMiddleware",  # Auto-login visitors from any page
    "apps.project_app.middleware.VisitorExpirationMiddleware",  # Redirect expired visitors to expiration page
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.project_app.middleware.GuestSessionMiddleware",
]

# ---------------------------------------
# Authentication Backends
# ---------------------------------------
AUTHENTICATION_BACKENDS = [
    # Django default authentication
    "django.contrib.auth.backends.ModelBackend",
    # django-allauth authentication (for social login)
    "allauth.account.auth_backends.AuthenticationBackend",
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------
# Templates
# ---------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.project_app.context_processors.version_context",
                "apps.project_app.context_processors.project_context",
                "apps.project_app.context_processors.visitor_expiration_context",
                "config.context_processors.cache_buster",
                "config.context_processors.debug_mode",
                "config.context_processors.scitex_version",
            ],
        },
    },
]


# ---------------------------------------
# Database - Fallback
# ---------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "data" / "db" / "sqlite" / "scitex_cloud.db",
    }
}

# Cache Configuration - fallback to database if Redis not available
REDIS_URL = os.getenv("SCITEX_CLOUD_REDIS_URL", "redis://127.0.0.1:6379/1")

try:
    import redis

    # Test Redis connection
    r = redis.from_url(REDIS_URL)
    r.ping()
    # Redis is available
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "scitex_cloud",
            "TIMEOUT": 3600,  # 1 hour default timeout
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
except (ImportError, Exception):
    # Redis not available, use database cache
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "cache_table",
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

SESSION_COOKIE_AGE = 86400  # 24 hours

# ---------------------------------------
# Password validation
# ---------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# ---------------------------------------
# Internationalization
# ---------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------
# Email
# ---------------------------------------
EMAIL_BACKEND = os.getenv("SCITEX_CLOUD_EMAIL_BACKEND")
EMAIL_HOST = os.getenv("SCITEX_CLOUD_EMAIL_HOST")
EMAIL_PORT = int(os.getenv("SCITEX_CLOUD_EMAIL_PORT", "587"))
EMAIL_USE_TLS = (
    os.getenv("SCITEX_CLOUD_EMAIL_USE_TLS", "True").lower() == "true"
)
EMAIL_HOST_USER = os.getenv("SCITEX_CLOUD_EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("SCITEX_CLOUD_EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER

# Site URL for generating absolute URLs in emails
SITE_URL = os.getenv("SCITEX_CLOUD_SITE_URL", "http://127.0.0.1:8000")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ASGI Configuration for Channels
ASGI_APPLICATION = "config.asgi.application"

# Channel Layers Configuration (fallback to in-memory if Redis unavailable)
try:
    import redis

    # Test Redis connection for channels
    redis_url = os.getenv("SCITEX_CLOUD_REDIS_URL", "redis://127.0.0.1:6379/2")
    r = redis.from_url(redis_url)
    r.ping()
    # Redis is available for channels
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [redis_url],
            },
        },
    }
except (ImportError, Exception):
    # Fallback to in-memory channel layer
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }

# ---------------------------------------
# Celery Configuration (Async Task Queue)
# ---------------------------------------
CELERY_BROKER_URL = os.getenv("SCITEX_CLOUD_REDIS_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max per task
CELERY_RESULT_EXTENDED = True

# Task routing to dedicated queues
CELERY_TASK_ROUTES = {
    "apps.writer_app.tasks.*": {"queue": "ai_queue"},
    "apps.scholar_app.tasks.*": {"queue": "search_queue"},
    "apps.code_app.tasks.*": {"queue": "compute_queue"},
    "apps.vis_app.tasks.*": {"queue": "vis_queue"},
}

# Fair scheduling: Rate limits per task (can be overridden per-user in code)
CELERY_TASK_ANNOTATIONS = {
    "apps.writer_app.tasks.ai_suggest": {"rate_limit": "10/m"},
    "apps.writer_app.tasks.ai_generate": {"rate_limit": "5/m"},
    "apps.scholar_app.tasks.search_papers": {"rate_limit": "30/m"},
    "apps.scholar_app.tasks.process_pdf": {"rate_limit": "20/m"},
}

# Worker configuration for fairness
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # One task at a time for fair scheduling
CELERY_WORKER_CONCURRENCY = 4  # Parallel workers

# Beat scheduler for periodic tasks (optional)
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Periodic task schedule
CELERY_BEAT_SCHEDULE = {
    # Collect server metrics every 5 seconds
    'collect-server-metrics': {
        'task': 'apps.public_app.tasks.collect_server_metrics',
        'schedule': 5.0,  # Every 5 seconds
        'options': {
            'expires': 4.0,  # Expire after 4 seconds if not started
        },
    },
    # Clean up expired visitor allocations every 5 minutes
    'cleanup-expired-visitor-allocations': {
        'task': 'apps.public_app.tasks.cleanup_expired_visitor_allocations',
        'schedule': 300.0,  # Every 5 minutes (in seconds)
        'options': {
            'expires': 270.0,  # Expire after 4.5 minutes if not started
        },
    },
    # Auto-unmount inactive remote projects every 10 minutes
    'auto-unmount-remote-projects': {
        'task': 'apps.project_app.tasks.auto_unmount_inactive_remote_projects',
        'schedule': 600.0,  # Every 10 minutes (in seconds)
        'options': {
            'expires': 540.0,  # Expire after 9 minutes if not started
        },
    },
    # Clean up stale mounts every hour
    'cleanup-stale-mounts': {
        'task': 'apps.project_app.tasks.cleanup_stale_mounts',
        'schedule': 3600.0,  # Every hour (in seconds)
        'options': {
            'expires': 3540.0,  # Expire after 59 minutes if not started
        },
    },
    # Generate server status charts every 1 minute
    'generate-status-charts': {
        'task': 'apps.public_app.tasks.generate_status_charts',
        'schedule': 60.0,  # Every 1 minute
        'options': {
            'expires': 55.0,  # Expire after 55 seconds if not started
        },
    },
}

# ---------------------------------------
# Logging
# ---------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "standard": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
            "formatter": "verbose",
        },
        "null": {
            "class": "logging.NullHandler",
        },
        # Django app logs
        "django_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "django.log"),
            "maxBytes": 5242880,  # 5MB
            "backupCount": 5,
            "formatter": "standard",
            "level": "INFO",
        },
        # Celery task logs
        "celery_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "celery.log"),
            "maxBytes": 5242880,  # 5MB
            "backupCount": 5,
            "formatter": "standard",
            "level": "INFO",
        },
        # SLURM job logs
        "slurm_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "slurm.log"),
            "maxBytes": 5242880,  # 5MB
            "backupCount": 3,
            "formatter": "standard",
            "level": "INFO",
        },
        # Git operations logs
        "git_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "git.log"),
            "maxBytes": 5242880,  # 5MB
            "backupCount": 3,
            "formatter": "standard",
            "level": "INFO",
        },
        # Error logs (all errors)
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "errors.log"),
            "maxBytes": 5242880,  # 5MB
            "backupCount": 5,
            "formatter": "standard",
            "level": "ERROR",
        },
    },
    "loggers": {
        # Django framework
        "django": {
            "handlers": ["django_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["django_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        # Celery tasks
        "celery": {
            "handlers": ["celery_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "celery.task": {
            "handlers": ["celery_file"],
            "level": "INFO",
            "propagate": False,
        },
        # SLURM jobs
        "scitex.slurm": {
            "handlers": ["slurm_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        # Git operations
        "scitex.git": {
            "handlers": ["git_file"],
            "level": "INFO",
            "propagate": False,
        },
        # SciTeX app (general)
        "scitex": {
            "handlers": ["django_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        # All errors
        "scitex.errors": {
            "handlers": ["error_file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# ---------------------------------------
# Integration
# ---------------------------------------
# ORCID OAuth (legacy - for profile linking)
ORCID_CLIENT_ID = os.getenv("ORCID_CLIENT_ID", "")
ORCID_CLIENT_SECRET = os.getenv("ORCID_CLIENT_SECRET", "")
ORCID_REDIRECT_URI = os.getenv(
    "ORCID_REDIRECT_URI", "http://localhost:8000/integrations/orcid/callback/"
)

# ---------------------------------------
# Django-Allauth Settings (Social Login)
# ---------------------------------------
# Required for django-allauth
SITE_ID = 1

# Allauth account settings
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_VERIFICATION = "optional"  # or "mandatory" for stricter verification
ACCOUNT_SIGNUP_REDIRECT_URL = LOGIN_REDIRECT_URL
ACCOUNT_LOGOUT_REDIRECT_URL = LOGOUT_REDIRECT_URL

# Social account settings
SOCIALACCOUNT_AUTO_SIGNUP = True  # Auto-create account on first social login
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True  # Allow login via email if account exists
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True  # Auto-connect social to existing account
SOCIALACCOUNT_LOGIN_ON_GET = True  # Allow GET requests for social login (for buttons)
SOCIALACCOUNT_QUERY_EMAIL = True  # Request email from providers

# Provider-specific settings
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
        "OAUTH_PKCE_ENABLED": True,
        "FETCH_USERINFO": True,
    },
    "orcid": {
        # Use sandbox.orcid.org for development, orcid.org for production
        "BASE_DOMAIN": os.getenv("ORCID_BASE_DOMAIN", "sandbox.orcid.org"),
        "MEMBER_API": False,  # Set True if you have ORCID member API access
    },
}

# Google OAuth credentials (from environment)
GOOGLE_CLIENT_ID = os.getenv("SCITEX_GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("SCITEX_GOOGLE_CLIENT_SECRET", "")

# Custom adapters for SciTeX-specific user handling
ACCOUNT_ADAPTER = "apps.auth_app.adapters.SciTexAccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.auth_app.adapters.SciTexSocialAccountAdapter"

# ---------------------------------------
# SciTeX Scholar Search Settings
# ---------------------------------------
# Enable/disable search pipeline caching
SCITEX_SCHOLAR_USE_CACHE = os.getenv(
    "SCITEX_SCHOLAR_USE_CACHE", "True"
).lower() in ["true", "1", "yes"]

# Maximum parallel workers for parallel search pipeline
SCITEX_SCHOLAR_MAX_WORKERS = int(os.getenv("SCITEX_SCHOLAR_MAX_WORKERS", "5"))

# Timeout per engine in seconds
SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE = int(
    os.getenv("SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE", "30")
)

# Preferred engines (comma-separated, e.g., "PubMed,CrossRef,arXiv")
SCITEX_SCHOLAR_ENGINES = os.getenv(
    "SCITEX_SCHOLAR_ENGINES", "CrossRef,PubMed,Semantic_Scholar,arXiv,OpenAlex"
).split(",")

# Default search mode: "parallel" or "single"
SCITEX_SCHOLAR_DEFAULT_MODE = os.getenv(
    "SCITEX_SCHOLAR_DEFAULT_MODE", "parallel"
)

# ---------------------------------------
# SciTeX Writer Settings
# ---------------------------------------
# Writer template path - can be set via environment variable or use default
# Check common locations for scitex-writer template
_WRITER_TEMPLATE_LOCATIONS = [
    Path(os.getenv("SCITEX_WRITER_TEMPLATE_PATH", "")),  # Explicit env var
    Path.home() / "proj" / "scitex-writer",  # Local clone
    Path("/tmp/scitex-writer"),  # Temp clone location
    BASE_DIR / "docs" / "scitex_writer_template",  # Extracted template
]

SCITEX_WRITER_TEMPLATE_PATH = None
for location in _WRITER_TEMPLATE_LOCATIONS:
    if location and location.exists():
        SCITEX_WRITER_TEMPLATE_PATH = location
        # Template found
        break

# ---------------------------------------
# CrossRef Local API
# ---------------------------------------
CROSSREF_INTERNAL_URL = os.getenv(
    "CROSSREF_INTERNAL_URL",
    "http://crossref:3333"
)

# ---------------------------------------
# REST Framework
# ---------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# ---------------------------------------
# JWT Settings
# ---------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# EOF
