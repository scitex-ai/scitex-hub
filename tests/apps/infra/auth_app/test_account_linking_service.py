#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Linking a login to a durable identity — including the refusal path.

The property under test is the operator's rule: ONE verified address means
ONE human. Two providers carrying the same verified address must fan in to a
single user, and an address already owned by somebody else must never be
taken over by a later login.

These tests touch the database because that is where the rule is actually
enforced — ``VerifiedEmail.email`` is unique, and a test that stubbed the
database would be testing the intention rather than the constraint.
"""

import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.contrib.auth.models import User

from apps.infra.auth_app.account_linking.models import (
    LinkedIdentity,
    VerifiedEmail,
)
from apps.infra.auth_app.account_linking.service import (
    EMAIL_OWNED_BY_ANOTHER_USER,
    LINKED,
    NO_VERIFIED_EMAIL,
    link_social_login,
)

SHARED = "shared@example.org"


def _verified_login(provider, uid, email=SHARED):
    account = SocialAccount(provider=provider, uid=uid, extra_data={"sub": uid})
    return SocialLogin(
        account=account,
        email_addresses=[EmailAddress(email=email, verified=True, primary=True)],
    )


def _unverified_login(provider, uid, email=SHARED):
    account = SocialAccount(provider=provider, uid=uid, extra_data={"sub": uid})
    return SocialLogin(
        account=account,
        email_addresses=[EmailAddress(email=email, verified=False, primary=True)],
    )


@pytest.mark.django_db
def test_verified_login_claims_the_address_for_that_user():
    # Arrange
    alice = User.objects.create_user(username="alice")
    # Act
    link_social_login(alice, _verified_login("google", "g-1"))
    # Assert
    assert VerifiedEmail.objects.get(email=SHARED).user_id == alice.pk


@pytest.mark.django_db
def test_verified_login_reports_linked():
    # Arrange
    alice = User.objects.create_user(username="alice")
    # Act
    result = link_social_login(alice, _verified_login("google", "g-1"))
    # Assert
    assert result.status == LINKED


@pytest.mark.django_db
def test_verified_login_records_the_provider_identity():
    # Arrange
    alice = User.objects.create_user(username="alice")
    # Act
    link_social_login(alice, _verified_login("google", "g-1"))
    # Assert
    assert LinkedIdentity.objects.filter(
        issuer="https://accounts.google.com", subject="g-1", user=alice
    ).exists()


@pytest.mark.django_db
def test_two_providers_with_one_address_fan_in_to_one_human():
    """The whole point of 'account linking' — Google + ORCID, one person."""
    # Arrange
    alice = User.objects.create_user(username="alice")
    link_social_login(alice, _verified_login("google", "g-1"))
    # Act
    link_social_login(alice, _verified_login("orcid", "0000-0002-1825-0097"))
    # Assert
    assert VerifiedEmail.objects.filter(email=SHARED).count() == 1


@pytest.mark.django_db
def test_two_providers_with_one_address_produce_two_identities():
    # Arrange
    alice = User.objects.create_user(username="alice")
    link_social_login(alice, _verified_login("google", "g-1"))
    # Act
    link_social_login(alice, _verified_login("orcid", "0000-0002-1825-0097"))
    # Assert
    assert LinkedIdentity.objects.filter(user=alice).count() == 2


@pytest.mark.django_db
def test_a_second_user_cannot_claim_an_owned_address():
    """The takeover refusal, at the storage layer rather than the adapter."""
    # Arrange
    alice = User.objects.create_user(username="alice")
    mallory = User.objects.create_user(username="mallory")
    link_social_login(alice, _verified_login("google", "g-1"))
    # Act
    result = link_social_login(mallory, _verified_login("orcid", "o-1"))
    # Assert
    assert result.status == EMAIL_OWNED_BY_ANOTHER_USER


@pytest.mark.django_db
def test_a_refused_claim_leaves_the_original_owner_intact():
    """The refusal must not half-apply — Alice still owns her address."""
    # Arrange
    alice = User.objects.create_user(username="alice")
    mallory = User.objects.create_user(username="mallory")
    link_social_login(alice, _verified_login("google", "g-1"))
    # Act
    link_social_login(mallory, _verified_login("orcid", "o-1"))
    # Assert
    assert VerifiedEmail.objects.get(email=SHARED).user_id == alice.pk


@pytest.mark.django_db
def test_an_unverified_address_is_never_stored():
    """Storing it would make an attacker-supplied string an account key."""
    # Arrange
    alice = User.objects.create_user(username="alice")
    # Act
    link_social_login(alice, _unverified_login("google", "g-1"))
    # Assert
    assert VerifiedEmail.objects.filter(email=SHARED).exists() is False


@pytest.mark.django_db
def test_a_login_without_a_verified_address_still_records_its_identity():
    """ORCID with no email is a valid identity; it just cannot be a key."""
    # Arrange
    alice = User.objects.create_user(username="alice")
    # Act
    link_social_login(alice, _unverified_login("orcid", "o-1"))
    # Assert
    assert LinkedIdentity.objects.filter(subject="o-1", user=alice).exists()


@pytest.mark.django_db
def test_a_login_without_a_verified_address_reports_that_state():
    # Arrange
    alice = User.objects.create_user(username="alice")
    # Act
    result = link_social_login(alice, _unverified_login("orcid", "o-1"))
    # Assert
    assert result.status == NO_VERIFIED_EMAIL


@pytest.mark.django_db
def test_relogin_does_not_duplicate_the_identity_row():
    """Linking runs on EVERY login, so it has to be idempotent."""
    # Arrange
    alice = User.objects.create_user(username="alice")
    link_social_login(alice, _verified_login("google", "g-1"))
    # Act
    link_social_login(alice, _verified_login("google", "g-1"))
    # Assert
    assert LinkedIdentity.objects.filter(subject="g-1").count() == 1


@pytest.mark.django_db
def test_address_case_does_not_create_a_second_account_key():
    """Alice@ and alice@ are one mailbox and must be one key."""
    # Arrange
    alice = User.objects.create_user(username="alice")
    link_social_login(alice, _verified_login("google", "g-1", email=SHARED))
    # Act
    link_social_login(alice, _verified_login("orcid", "o-1", email=SHARED.upper()))
    # Assert
    assert VerifiedEmail.objects.count() == 1


# EOF
