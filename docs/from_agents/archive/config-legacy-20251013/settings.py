#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-06-27 06:30:42 (ywatanabe)"
# File: /ssh:scitex:/home/ywatanabe/proj/scitex-cloud/config/settings.py
# ----------------------------------------
import os
__FILE__ = (
    "./config/settings.py"
)
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Django settings for SciTeX Cloud project.
Base settings shared across all environments.
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SCITEX_CLOUD_DJANGO_SECRET_KEY = os.environ.get(
    "SCITEX_CLOUD_DJANGO_SECRET_KEY",
    "django-insecure-development-key-change-in-production",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

SCITEX_CLOUD_ALLOWED_HOSTS = []

# Application definition
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
    "corsheaders",
    "widget_tweaks",
]

LOCAL_APPS = [
    "apps.workspace_app.apps.CoreAppConfig",
    "apps.engine_app.apps.EngineAppConfig",
    "apps.scholar_app.apps.ScholarConfig",  # Fixed: Use scholar_app instead of scholar
    "apps.code_app.apps.CodeAppConfig",
    "apps.writer_app.apps.WriterAppConfig",
    "apps.viz_app.apps.VizAppConfig",
    "apps.cloud_app.apps.CloudAppConfig",
    "apps.billing_app.apps.BillingAppConfig",
    "apps.monitoring_app.apps.MonitoringAppConfig",
    "apps.orcid_app.apps.OrcidAppConfig",
    "apps.mendeley_app.apps.MendeleyAppConfig",
    "apps.reference_sync_app.apps.ReferenceSyncAppConfig",
    "apps.github_app.apps.GithubAppConfig",
    "apps.collaboration_app.apps.CollaborationAppConfig",
    "apps.ai_assistant_app.apps.AiAssistantAppConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.billing_app.middleware.FeatureAccessMiddleware",
    "apps.billing_app.middleware.SubscriptionStatusMiddleware",
    "apps.billing_app.middleware.UsageTrackingMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "data" / "scitex_cloud.db",
    }
}

# Password validation
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

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Base logging configuration (shared between environments)
# More specific configurations in development.py and production.py
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
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.template": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "scitex": {  # Application-specific logger
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# ORCID Integration Settings
ORCID_CLIENT_ID = os.environ.get('ORCID_CLIENT_ID', 'your-orcid-client-id')
ORCID_CLIENT_SECRET = os.environ.get('ORCID_CLIENT_SECRET', 'your-orcid-client-secret')
ORCID_SANDBOX = os.environ.get('ORCID_SANDBOX', 'true').lower() == 'true'

# Reference Manager Integration Settings
MENDELEY_CLIENT_ID = os.environ.get('MENDELEY_CLIENT_ID', '')
MENDELEY_CLIENT_SECRET = os.environ.get('MENDELEY_CLIENT_SECRET', '')
ZOTERO_CLIENT_ID = os.environ.get('ZOTERO_CLIENT_ID', '')
ZOTERO_CLIENT_SECRET = os.environ.get('ZOTERO_CLIENT_SECRET', '')

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# GitHub Integration Settings
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID', 'your-github-client-id')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET', 'your-github-client-secret')
GITHUB_REDIRECT_URI = os.environ.get('GITHUB_REDIRECT_URI', 'http://localhost:8000/github/callback/')
GITHUB_WEBHOOK_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', 'your-webhook-secret')

# Stripe Payment Processing Settings
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_SCITEX_CLOUD_DJANGO_SECRET_KEY = os.environ.get('STRIPE_SCITEX_CLOUD_DJANGO_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# Billing and Monetization Settings
BILLING_ENABLED = os.environ.get('BILLING_ENABLED', 'true').lower() == 'true'
FREE_TIER_LIMITS = {
    'max_projects': 1,
    'storage_gb': 1,
    'compute_hours_monthly': 5,
    'gpu_hours_monthly': 1,
    'api_calls_monthly': 100,
}

# Email settings for billing notifications
if BILLING_ENABLED:
    SCITEX_CLOUD_EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    SCITEX_CLOUD_EMAIL_HOST = os.environ.get('SCITEX_CLOUD_EMAIL_HOST', 'smtp.gmail.com')
    SCITEX_CLOUD_EMAIL_PORT = int(os.environ.get('SCITEX_CLOUD_EMAIL_PORT', '587'))
    SCITEX_CLOUD_EMAIL_USE_TLS = os.environ.get('SCITEX_CLOUD_EMAIL_USE_TLS', 'true').lower() == 'true'
    SCITEX_CLOUD_EMAIL_HOST_USER = os.environ.get('SCITEX_CLOUD_EMAIL_HOST_USER', '')
    SCITEX_CLOUD_EMAIL_HOST_PASSWORD = os.environ.get('SCITEX_CLOUD_EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'billing@scitex.ai')

# EOF
