#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression test for account takeover via unverified social email.

THE VULNERABILITY. ``SciTexSocialAccountAdapter.pre_social_login`` used to
read ``sociallogin.account.extra_data["email"]`` and, on a bare
``email__iexact`` match, call ``sociallogin.connect(request, existing_user)``
— with no check that the provider had VERIFIED the address.

An address in a provider payload is a CLAIM, not a fact. Any provider willing
to assert an address it never checked (or any attacker who can register that
address at such a provider) could therefore sign straight into the existing
SciTeX account using it. On a public site that is full account takeover, and
it needs no interaction from the victim.

THE PROOF. ``test_unverified_address_does_not_connect_to_the_victim`` fails
on the pre-patch adapter (a SocialAccount is created against the victim) and
passes after it. The companion test shows the fix did not simply disable the
feature: a genuinely verified address still connects.

No mocks (project rule) — real allauth objects and a real request carrying a
real session, because ``connect()`` writes through the session.
"""

import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialLogin
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sites.models import Site
from django.test import RequestFactory

from apps.infra.auth_app.adapters import SciTexSocialAccountAdapter

VICTIM_EMAIL = "victim@example.org"


@pytest.fixture
def google_app(db):
    """A real SocialApp row — ``connect()`` resolves the provider through it.

    Real, not a stub: allauth looks the app up in the database, so the row is
    what makes the connect path exercise its actual code.
    """
    app = SocialApp.objects.create(
        provider="google", name="Google", client_id="cid", secret="secret"
    )
    app.sites.add(Site.objects.get_current())
    return app


def _request():
    """A real request with a real session — ``connect()`` needs both."""
    request = RequestFactory().get("/accounts/google/login/callback/")
    SessionMiddleware(lambda req: None).process_request(request)
    MessageMiddleware(lambda req: None).process_request(request)
    request.session.save()
    request.user = AnonymousUser()
    return request


def _login_claiming(email, *, verified):
    """A social login asserting ``email``, verified or merely claimed."""
    account = SocialAccount(
        provider="google",
        uid="attacker-uid",
        extra_data={"email": email, "email_verified": verified},
    )
    return SocialLogin(
        account=account,
        email_addresses=[
            EmailAddress(email=email, verified=verified, primary=True)
        ],
    )


@pytest.mark.django_db
def test_unverified_address_does_not_connect_to_the_victim(google_app):
    """THE SECURITY REGRESSION.

    Measured red/green against the pre-patch adapter (2026-08-14): with the
    old ``pre_social_login`` this assertion FAILS because the attacker's
    social account really is attached to the victim's user row. The
    ``google_app`` fixture matters here — without it the old code still
    reached ``connect()`` but died on a missing SocialApp, which proves the
    same thing far less legibly. With the app present the old path succeeds,
    so the failure reads as what it is: takeover.
    """
    # Arrange
    victim = User.objects.create_user(
        username="victim", email=VICTIM_EMAIL, password="victim-password"
    )
    sociallogin = _login_claiming(VICTIM_EMAIL, verified=False)
    # Act
    SciTexSocialAccountAdapter().pre_social_login(_request(), sociallogin)
    # Assert
    assert SocialAccount.objects.filter(user=victim).exists() is False


@pytest.mark.django_db
def test_verified_address_still_connects_to_the_existing_account(google_app):
    """The fix must not be 'turn the feature off'."""
    # Arrange
    victim = User.objects.create_user(
        username="victim", email=VICTIM_EMAIL, password="victim-password"
    )
    sociallogin = _login_claiming(VICTIM_EMAIL, verified=True)
    # Act
    SciTexSocialAccountAdapter().pre_social_login(_request(), sociallogin)
    # Assert
    assert sociallogin.user == victim


@pytest.mark.django_db
def test_no_matching_user_is_left_alone(google_app):
    """An address nobody holds must not connect to anybody."""
    # Arrange
    User.objects.create_user(username="someone", email="other@example.org")
    sociallogin = _login_claiming(VICTIM_EMAIL, verified=True)
    # Act
    SciTexSocialAccountAdapter().pre_social_login(_request(), sociallogin)
    # Assert
    assert SocialAccount.objects.exists() is False


# EOF
