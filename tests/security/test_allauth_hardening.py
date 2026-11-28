"""allauth and OAuth provider hardening, driven through real requests.

- Social login and allauth logout change state only on POST.
- Proven addresses: the hub's one-time-code proof is recorded where allauth
  reads it, and an account with no proof is asked to confirm at sign-in
  instead of being locked out.
- The OAuth provider requires PKCE, with a narrow, explicit exemption for a
  confidential client that is still migrating.
"""

from __future__ import annotations

import json

import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialApp
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core import mail
from django.test import Client, override_settings
from oauth2_provider.models import get_application_model

from apps.infra.auth_app.models import EmailVerification, PendingSignup
from apps.infra.auth_app.oauth_validator import SciTexOAuth2Validator

pytestmark = [pytest.mark.security, pytest.mark.django_db]

PASSWORD = "Correct-Horse-Battery-9"  # pragma: allowlist secret
GOOGLE_LOGIN = "/auth/social/google/login/"


@pytest.fixture
def google_app():
    app = SocialApp.objects.create(
        provider="google", name="Google", client_id="cid", secret="secret"
    )
    app.sites.add(Site.objects.get_current())
    return app


@pytest.fixture
def member():
    return User.objects.create_user(
        username="member", email="member@example.org", password=PASSWORD
    )


def _oauth_app(client_type):
    return get_application_model().objects.create(
        name=f"probe-{client_type}",
        client_type=client_type,
        authorization_grant_type="authorization-code",
        redirect_uris="https://client.example/callback",
    )


# -- state changes are POST-only ---------------------------------------------


def test_social_login_get_does_not_leave_for_the_provider(google_app):
    # Arrange
    client = Client()
    # Act
    response = client.get(GOOGLE_LOGIN)
    # Assert
    assert response.status_code == 200


def test_social_login_post_redirects_to_the_provider(google_app):
    # Arrange
    client = Client()
    # Act
    response = client.post(GOOGLE_LOGIN)
    # Assert
    assert response["Location"].startswith("https://accounts.google.com/")


def test_allauth_logout_get_keeps_the_session(member):
    # Arrange
    client = Client()
    client.force_login(member)
    # Act
    client.get("/auth/social/logout/")
    # Assert
    assert client.session.get("_auth_user_id") == str(member.pk)


# -- proven addresses ----------------------------------------------------------


def test_code_verified_signup_records_a_verified_address():
    # Arrange
    user = User.objects.create_user(
        username="fresh", email="fresh@example.org", password=PASSWORD, is_active=False
    )
    PendingSignup.objects.create(user=user, email=user.email)
    code = EmailVerification.objects.create(user=user, email=user.email).code
    # Act
    Client().post(
        "/auth/api/verify-email/",
        data=json.dumps({"email": user.email, "otp_code": code}),
        content_type="application/json",
    )
    # Assert
    assert EmailAddress.objects.filter(
        user=user, email="fresh@example.org", verified=True, primary=True
    ).exists()


def test_unproven_account_still_signs_in(member):
    # Arrange
    client = Client()
    # Act
    client.post("/auth/signin/", {"username": member.username, "password": PASSWORD})
    # Assert
    assert client.session.get("_auth_user_id") == str(member.pk)


def test_unproven_account_is_sent_a_confirmation_at_sign_in(member):
    # Arrange: allauth rate-limits confirmation mail per address in the cache,
    # which other tests on this worker may already have used for this address.
    from django.core.cache import cache

    cache.clear()
    client = Client()
    mail.outbox.clear()
    # Act
    client.post("/auth/signin/", {"username": member.username, "password": PASSWORD})
    # Assert
    assert [m.to for m in mail.outbox] == [[member.email]]


def test_proven_account_is_not_sent_a_confirmation(member):
    # Arrange
    EmailAddress.objects.create(
        user=member, email=member.email, verified=True, primary=True
    )
    client = Client()
    mail.outbox.clear()
    # Act
    client.post("/auth/signin/", {"username": member.username, "password": PASSWORD})
    # Assert
    assert mail.outbox == []


def _run_backfill():
    import importlib

    from django.apps import apps

    module = importlib.import_module(
        "apps.infra.auth_app.migrations.0016_record_verified_email_addresses"
    )
    module.record_proven_addresses(apps, None)


def test_backfill_records_a_code_proven_address():
    # Arrange
    user = User.objects.create_user(
        username="coded", email="Coded@Example.org", password=PASSWORD
    )
    EmailVerification.objects.create(
        user=user, email="coded@example.org", is_verified=True
    )
    # Act
    _run_backfill()
    # Assert
    assert EmailAddress.objects.filter(
        user=user, email="coded@example.org", verified=True
    ).exists()


def test_backfill_records_a_provider_proven_address():
    # Arrange
    from allauth.socialaccount.models import SocialAccount

    user = User.objects.create_user(username="linked", email="linked@example.org")
    SocialAccount.objects.create(
        user=user,
        provider="google",
        uid="g-1",
        extra_data={"email": "linked@example.org", "email_verified": True},
    )
    # Act
    _run_backfill()
    # Assert
    assert EmailAddress.objects.filter(user=user, verified=True).exists()


def test_backfill_leaves_an_unproven_account_unverified(member):
    # Arrange
    EmailVerification.objects.create(
        user=member, email="old@example.org", is_verified=True
    )
    # Act
    _run_backfill()
    # Assert
    assert not EmailAddress.objects.filter(user=member, verified=True).exists()


# -- PKCE ------------------------------------------------------------------------


def test_pkce_is_required_for_a_public_client():
    # Arrange
    app = _oauth_app("public")
    # Act
    required = SciTexOAuth2Validator().is_pkce_required(app.client_id, None)
    # Assert
    assert required is True


def test_pkce_is_required_for_a_confidential_client_by_default():
    # Arrange
    app = _oauth_app("confidential")
    # Act
    required = SciTexOAuth2Validator().is_pkce_required(app.client_id, None)
    # Assert
    assert required is True


def test_listed_confidential_client_may_skip_pkce_while_migrating():
    # Arrange
    app = _oauth_app("confidential")
    # Act
    with override_settings(OAUTH_PKCE_EXEMPT_CLIENT_IDS=frozenset({app.client_id})):
        required = SciTexOAuth2Validator().is_pkce_required(app.client_id, None)
    # Assert
    assert required is False


def test_listing_a_public_client_does_not_exempt_it():
    # Arrange
    app = _oauth_app("public")
    # Act
    with override_settings(OAUTH_PKCE_EXEMPT_CLIENT_IDS=frozenset({app.client_id})):
        required = SciTexOAuth2Validator().is_pkce_required(app.client_id, None)
    # Assert
    assert required is True
