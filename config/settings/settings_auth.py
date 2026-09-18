# -*- coding: utf-8 -*-
# File: config/settings/settings_auth.py
"""Authentication and OAuth settings for SciTeX Hub."""

import os
import socket
from urllib.parse import urlparse
from datetime import timedelta

import scitex as stx

from config.social_apps import orcid_base_domain, with_credential_apps

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

# Google credentials, read here because they are half of the provider
# configuration below (they used to be declared further down, after the
# configuration that now consumes them).
GOOGLE_CLIENT_ID = os.getenv("SCITEX_HUB_GOOGLE_CLIENT_ID") or os.getenv(
    "SCITEX_GOOGLE_CLIENT_ID", ""
)
GOOGLE_CLIENT_SECRET = os.getenv("SCITEX_HUB_GOOGLE_CLIENT_SECRET") or os.getenv(
    "SCITEX_GOOGLE_CLIENT_SECRET", ""
)

# ---------------------------------------
# Django-Allauth Settings (Social Login)
# ---------------------------------------
SITE_ID = 1

#: The domain django.contrib.sites hands out for THIS deployment.
#:
#: DERIVED, NOT A SECOND VARIABLE. hub already configures its public address
#: as SCITEX_HUB_SITE_URL (settings_shared.py: SITE_URL), and prod already
#: sets it to https://scitex.ai. Introducing a separate SCITEX_HUB_SITE_DOMAIN
#: would give one fact two sources that can disagree -- and the failure mode of
#: disagreement here is invisible, which is the whole reason this code exists.
#: So the Site domain is the host part of the URL we already have.
#:
#: SITE_ID pins allauth and Django to one Site row, so this value is not
#: decorative: it is the host used to build OAuth callback URLs and the links
#: inside confirmation and password-reset email. A wrong value raises nowhere --
#: it silently produces URLs nobody can reach.
#:
#: EMPTY when SCITEX_HUB_SITE_URL was never set, deliberately. SITE_URL falls
#: back to http://127.0.0.1:8000 for local development, and deriving the Site
#: domain from that fallback is exactly how production came to hold
#: "127.0.0.1:8000". `manage.py sync_site_domain` refuses on empty rather than
#: stamping a development host onto whatever database it is pointed at.
#: Read the ENV VAR rather than settings_shared.SITE_URL on purpose. This
#: module is imported BY settings_shared (settings_shared.py:457), so a bare
#: `SITE_URL` here resolves in this module's own namespace and would be a
#: NameError, and importing it back would be a circular import into a
#: half-initialised module. The env var is the same single source either way.
_SITE_URL = (
    os.getenv("SCITEX_HUB_SITE_URL", "") or os.getenv("SITE_URL", "")
).strip()
SITE_DOMAIN = urlparse(_SITE_URL).netloc.strip() if _SITE_URL else ""

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

# Provider configuration, plus the app that makes each provider clickable.
#
# THE APP COMES FROM THE CREDENTIALS, HERE, AND NOT ONLY FROM THE DATABASE.
# allauth reads an app from `SocialApp` rows OR from SOCIALACCOUNT_PROVIDERS
# [provider]["APP"]. This deployment's credentials arrive in the environment
# and previously reached allauth only via `manage.py setup_social_auth`, so a
# deployment holding complete credentials still rendered no button (and could
# not log in socially) until someone ran that command. `with_credential_apps`
# attaches the app for every provider whose pair is COMPLETE; an incomplete or
# placeholder pair attaches nothing, because a half-built app turns into an
# HTTP 500 at the token exchange rather than at render time.
# See config/social_apps.py for the rule and tests/apps/auth_app/
# test_social_provider_credentials.py for what it guarantees.
SOCIALACCOUNT_PROVIDERS = with_credential_apps(
    {
        "google": {
            "SCOPE": ["profile", "email"],
            "AUTH_PARAMS": {"access_type": "online"},
            "OAUTH_PKCE_ENABLED": True,
            "FETCH_USERINFO": True,
        },
        "orcid": {
            # ALLOWLISTED, not read straight from the environment. allauth
            # concatenates this value into the authorize URL and into
            # `https://pub.{value}/oauth/token`, which is where the client
            # SECRET is POSTed — so `ORCID_BASE_DOMAIN=attacker.invalid` used to
            # hand the secret to a host we do not own. `orcid_base_domain`
            # accepts only ORCID's two hosts (tolerating the URL/case forms an
            # operator might paste) and RAISES here otherwise: this module must
            # not load with an endpoint it cannot vouch for.
            "BASE_DOMAIN": orcid_base_domain(os.getenv("ORCID_BASE_DOMAIN")),
            "MEMBER_API": False,
        },
    },
    {
        "google": (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        "orcid": (ORCID_CLIENT_ID, ORCID_CLIENT_SECRET),
    },
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
