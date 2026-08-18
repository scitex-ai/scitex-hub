# -*- coding: utf-8 -*-
# File: config/settings/settings_auth.py
"""Authentication and OAuth settings for SciTeX Hub."""

import os
import socket
from datetime import timedelta

import scitex as stx

# ---------------------------------------
# ORCID OAuth (legacy - for profile linking)
# ---------------------------------------
ORCID_CLIENT_ID = os.getenv("SCITEX_HUB_ORCID_CLIENT_ID") or os.getenv(
    "ORCID_CLIENT_ID", ""
)
ORCID_CLIENT_SECRET = os.getenv("SCITEX_HUB_ORCID_CLIENT_SECRET") or os.getenv(
    "ORCID_CLIENT_SECRET", ""
)
ORCID_REDIRECT_URI = os.getenv(
    "ORCID_REDIRECT_URI", "http://localhost:8000/integrations/orcid/callback/"
)

# ---------------------------------------
# Django-Allauth Settings (Social Login)
# ---------------------------------------
SITE_ID = 1

#: The domain django.contrib.sites hands out for THIS deployment.
#:
#: SITE_ID pins allauth and Django to one Site row, so this value is not
#: decorative: it is the host used to build OAuth callback URLs and the links
#: inside confirmation and password-reset email. A wrong value does not raise
#: anywhere -- it silently produces URLs nobody can reach.
#:
#: Deliberately EMPTY when unset. Production was found holding "127.0.0.1:8000"
#: because a management command defaulted to that literal, so a default here
#: would reintroduce exactly the failure this replaces. `manage.py
#: sync_site_domain` refuses and names this variable instead of guessing.
SITE_DOMAIN = os.getenv("SCITEX_HUB_SITE_DOMAIN", "").strip()

#: Human-readable label for the same Site row. Cosmetic, unlike SITE_DOMAIN.
SITE_NAME = os.getenv("SCITEX_HUB_SITE_NAME", "SciTeX").strip()

ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_METHODS = {"email", "username"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_SIGNUP_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/"
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = False

# Social account settings
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_QUERY_EMAIL = True

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
        "FETCH_USERINFO": True,
    },
    "orcid": {
        "BASE_DOMAIN": os.getenv("ORCID_BASE_DOMAIN", "sandbox.orcid.org"),
        "MEMBER_API": False,
    },
}

GOOGLE_CLIENT_ID = os.getenv("SCITEX_HUB_GOOGLE_CLIENT_ID") or os.getenv(
    "SCITEX_GOOGLE_CLIENT_ID", ""
)
GOOGLE_CLIENT_SECRET = os.getenv("SCITEX_HUB_GOOGLE_CLIENT_SECRET") or os.getenv(
    "SCITEX_GOOGLE_CLIENT_SECRET", ""
)

ACCOUNT_ADAPTER = "apps.infra.auth_app.adapters.SciTexAccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.infra.auth_app.adapters.SciTexSocialAccountAdapter"

# ---------------------------------------
# Account linking (scitex.ai identity)
# ---------------------------------------
# This instance's name inside the fleet, e.g. "scitex-nas-03" for scitex.ai.
# Several scitex.ai instances share a cards store that synchronises across
# hosts, so a user record has to say which instance minted it — that is what
# the cards-side ``host_at_name`` join key is for.
#
# Defaults to the machine hostname, which is right for a single-instance
# deployment and wrong for nothing: it is a real, distinct value rather than
# a placeholder that silently collides. Set it explicitly in SECRET/.env.*
# when the instance name differs from the hostname.
SCITEX_INSTANCE_NAME = os.getenv("SCITEX_INSTANCE_NAME") or socket.gethostname()


# ---------------------------------------
# OAuth2 Provider (django-oauth-toolkit)
# Allows external apps (e.g. orochi.scitex.ai) to "Sign in with SciTeX"
# ---------------------------------------
OAUTH2_PROVIDER = {
    "SCOPES": {
        "openid": "OpenID Connect",
        "profile": "User profile",
        "email": "Email address",
    },
    "DEFAULT_SCOPES": ["openid", "profile", "email"],
    "OIDC_ENABLED": False,
    "OAUTH2_VALIDATOR_CLASS": "apps.infra.auth_app.oauth_validator.SciTexOAuth2Validator",
    "ACCESS_TOKEN_EXPIRE_SECONDS": 3600,
    "REFRESH_TOKEN_EXPIRE_SECONDS": 86400 * 30,
    "PKCE_REQUIRED": False,
}


# ---------------------------------------
# JWT Settings
# ---------------------------------------
def get_simple_jwt_settings(secret_key: str) -> dict:
    """Build SIMPLE_JWT settings. Called by settings_shared with SECRET_KEY."""
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


@stx.session
def main(CONFIG=stx.session.INJECTED):
    """Settings module — not meant to be executed directly."""
    return 0


if __name__ == "__main__":
    main()

# EOF
