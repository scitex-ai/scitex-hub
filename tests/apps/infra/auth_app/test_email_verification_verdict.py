#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The gate that decides whether an address may key an account.

This is the security core of account linking. If ``is_account_key`` is ever
True for an address the provider did not vouch for, then anyone who can make
a provider echo back a victim's address can sign in as the victim. So these
tests pin the FAIL-CLOSED behaviour, not the happy path — the happy path
failing is an outage, this failing is a breach.

No mocks (project rule): the inputs are real allauth ``EmailAddress`` /
``SocialAccount`` / ``SocialLogin`` objects, merely unsaved.
"""

import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialLogin

from apps.infra.auth_app.account_linking.verification import (
    UNKNOWN,
    UNVERIFIED,
    VERIFIED,
    EmailVerdict,
    EmailVerdictError,
    normalize_email,
    verified_email_of,
)

VICTIM = "victim@example.org"


def _login(*, addresses=None, extra_data=None, provider="google"):
    """A real SocialLogin carrying the given parsed addresses / raw payload."""
    account = SocialAccount(
        provider=provider, uid="uid-1", extra_data=extra_data or {}
    )
    return SocialLogin(account=account, email_addresses=addresses or [])


def test_verified_verdict_without_an_address_is_refused():
    """This shape would let the empty string become an account key."""
    # Arrange
    bad_kwargs = {"email": None, "status": VERIFIED, "source": "test"}
    # Act / guarded below
    # Assert
    with pytest.raises(EmailVerdictError):
        EmailVerdict(**bad_kwargs)


def test_unknown_status_value_is_refused():
    # Arrange
    bad_kwargs = {"email": VICTIM, "status": "probably", "source": "test"}
    # Act / guarded below
    # Assert
    with pytest.raises(EmailVerdictError):
        EmailVerdict(**bad_kwargs)


def test_case_is_folded_so_one_mailbox_is_one_key():
    """Without folding, Victim@ and victim@ are two keys for one mailbox."""
    # Arrange
    raw = "  Victim@Example.ORG "
    # Act
    result = normalize_email(raw)
    # Assert
    assert result == VICTIM


def test_non_string_address_is_rejected():
    # Arrange
    raw = 12345
    # Act
    result = normalize_email(raw)
    # Assert
    assert result is None


def test_provider_verified_address_keys_an_account():
    # Arrange
    login = _login(
        addresses=[EmailAddress(email=VICTIM, verified=True, primary=True)]
    )
    # Act
    verdict = verified_email_of(login)
    # Assert
    assert verdict.is_account_key is True


def test_unverified_address_does_not_key_an_account():
    """The takeover case: provider supplied the address but vouched nothing."""
    # Arrange
    login = _login(
        addresses=[EmailAddress(email=VICTIM, verified=False, primary=True)]
    )
    # Act
    verdict = verified_email_of(login)
    # Assert
    assert verdict.is_account_key is False


def test_unverified_is_reported_distinctly_from_unknown():
    """'Gave an address, did not vouch' is not the same as 'gave nothing'."""
    # Arrange
    login = _login(
        addresses=[EmailAddress(email=VICTIM, verified=False, primary=True)]
    )
    # Act
    verdict = verified_email_of(login)
    # Assert
    assert verdict.status == UNVERIFIED


def test_a_verified_address_wins_over_an_earlier_unverified_one():
    """Order must not decide the verdict, or a provider listing an
    unverified primary first would silently downgrade a real one."""
    # Arrange
    login = _login(
        addresses=[
            EmailAddress(email="other@example.org", verified=False, primary=True),
            EmailAddress(email=VICTIM, verified=True, primary=False),
        ]
    )
    # Act
    verdict = verified_email_of(login)
    # Assert
    assert verdict.email == VICTIM


def test_raw_payload_boolean_claim_is_honoured():
    # Arrange
    login = _login(extra_data={"email": VICTIM, "email_verified": True})
    # Act
    verdict = verified_email_of(login)
    # Assert
    assert verdict.is_account_key is True


def test_raw_payload_string_true_claim_is_honoured():
    """Some providers type the OIDC boolean as the string 'true'."""
    # Arrange
    login = _login(extra_data={"email": VICTIM, "email_verified": "true"})
    # Act
    verdict = verified_email_of(login)
    # Assert
    assert verdict.is_account_key is True


def test_raw_payload_without_a_claim_does_not_key_an_account():
    """The dangerous default — an address carrying no verification claim."""
    # Arrange
    login = _login(extra_data={"email": VICTIM})
    # Act
    verdict = verified_email_of(login)
    # Assert
    assert verdict.is_account_key is False


def test_raw_payload_false_claim_does_not_key_an_account():
    # Arrange
    login = _login(extra_data={"email": VICTIM, "email_verified": False})
    # Act
    verdict = verified_email_of(login)
    # Assert
    assert verdict.is_account_key is False


def test_non_affirmative_claim_string_does_not_key_an_account():
    """Only an explicit true counts; 'yes' is not the claim."""
    # Arrange
    login = _login(extra_data={"email": VICTIM, "email_verified": "yes"})
    # Act
    verdict = verified_email_of(login)
    # Assert
    assert verdict.is_account_key is False


def test_legacy_verified_email_spelling_is_honoured():
    # Arrange
    login = _login(extra_data={"email": VICTIM, "verified_email": True})
    # Act
    verdict = verified_email_of(login)
    # Assert
    assert verdict.is_account_key is True


def test_login_carrying_no_address_is_unknown():
    """ORCID commonly returns no address at all — a real, valid state."""
    # Arrange
    login = _login()
    # Act
    verdict = verified_email_of(login)
    # Assert
    assert verdict.status == UNKNOWN


def test_login_carrying_no_address_does_not_key_an_account():
    # Arrange
    login = _login()
    # Act
    verdict = verified_email_of(login)
    # Assert
    assert verdict.is_account_key is False


# EOF
