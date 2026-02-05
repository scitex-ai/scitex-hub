#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2026-02-04
# File: config/settings/settings_auth.py
"""Authentication and OAuth settings for SciTeX Cloud."""

import os
from datetime import timedelta

# ORCID OAuth (legacy - for profile linking)
ORCID_CLIENT_ID = os.getenv("SCITEX_CLOUD_ORCID_CLIENT_ID") or os.getenv(
    "ORCID_CLIENT_ID", ""
)
ORCID_CLIENT_SECRET = os.getenv("SCITEX_CLOUD_ORCID_CLIENT_SECRET") or os.getenv(
    "ORCID_CLIENT_SECRET", ""
)
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
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_SIGNUP_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/"

# Allow authenticated users to access signup/login pages
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = False

# Social account settings
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_QUERY_EMAIL = True

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
        "BASE_DOMAIN": os.getenv("ORCID_BASE_DOMAIN", "sandbox.orcid.org"),
        "MEMBER_API": False,
    },
}

# Google OAuth credentials
GOOGLE_CLIENT_ID = os.getenv("SCITEX_CLOUD_GOOGLE_CLIENT_ID") or os.getenv(
    "SCITEX_GOOGLE_CLIENT_ID", ""
)
GOOGLE_CLIENT_SECRET = os.getenv("SCITEX_CLOUD_GOOGLE_CLIENT_SECRET") or os.getenv(
    "SCITEX_GOOGLE_CLIENT_SECRET", ""
)

# Custom adapters for SciTeX-specific user handling
ACCOUNT_ADAPTER = "apps.auth_app.adapters.SciTexAccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.auth_app.adapters.SciTexSocialAccountAdapter"


# ---------------------------------------
# JWT Settings
# ---------------------------------------
def get_simple_jwt_settings(secret_key: str) -> dict:
    """Get SIMPLE_JWT settings. Requires SECRET_KEY from main settings."""
    return {
        "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
        "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
        "ROTATE_REFRESH_TOKENS": True,
        "BLACKLIST_AFTER_ROTATION": True,
        "UPDATE_LAST_LOGIN": True,
        "ALGORITHM": "HS256",
        "SIGNING_KEY": secret_key,
        "AUTH_HEADER_TYPES": ("Bearer",),
        "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
        "USER_ID_FIELD": "id",
        "USER_ID_CLAIM": "user_id",
    }


# EOF
