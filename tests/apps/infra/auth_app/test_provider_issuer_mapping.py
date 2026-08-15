#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provider identity: the ``(issuer, subject)`` pair, and the mapping gate.

The important test in this file is the LAST one. It is the mechanical
barrier that makes the fail-loud design safe: enabling a social provider in
settings without assigning it an issuer breaks CI here, instead of breaking a
user's login in production.
"""

import pytest
from allauth.socialaccount.models import SocialAccount, SocialLogin

from apps.infra.auth_app.account_linking.providers import (
    LOCAL_ISSUER,
    PROVIDER_ISSUERS,
    OidcIdentity,
    UnmappedProviderError,
    configured_providers_are_mapped,
    oidc_identity_for,
    provider_issuer,
)


def _login(provider, uid="uid-1", extra_data=None):
    account = SocialAccount(
        provider=provider, uid=uid, extra_data=extra_data or {}
    )
    return SocialLogin(account=account)


def test_google_maps_to_its_published_issuer():
    # Arrange
    provider = "google"
    # Act
    issuer = provider_issuer(provider)
    # Assert
    assert issuer == "https://accounts.google.com"


def test_orcid_maps_to_its_published_issuer():
    # Arrange
    provider = "orcid"
    # Act
    issuer = provider_issuer(provider)
    # Assert
    assert issuer == "https://orcid.org"


def test_unmapped_provider_raises_rather_than_inventing_an_issuer():
    """Inventing one would re-key every row the day the real issuer lands."""
    # Arrange
    provider = "facebook"
    # Act / guarded below
    # Assert
    with pytest.raises(UnmappedProviderError):
        provider_issuer(provider)


def test_unmapped_provider_error_names_the_file_to_edit():
    """An error that only says what broke is half-written."""
    # Arrange
    provider = "facebook"
    # Act
    try:
        provider_issuer(provider)
        message = ""
    except UnmappedProviderError as exc:
        message = str(exc)
    # Assert
    assert "providers.py" in message


def test_oidc_sub_claim_is_preferred_as_the_subject():
    # Arrange
    login = _login("google", uid="uid-1", extra_data={"sub": "google-sub-42"})
    # Act
    identity = oidc_identity_for(login)
    # Assert
    assert identity.subject == "google-sub-42"


def test_uid_is_the_subject_when_the_payload_omits_sub():
    """A provider can populate uid during token exchange and omit the claim."""
    # Arrange
    login = _login("google", uid="uid-fallback", extra_data={})
    # Act
    identity = oidc_identity_for(login)
    # Assert
    assert identity.subject == "uid-fallback"


def test_orcid_subject_is_the_orcid_id():
    """ORCID's stable subject is the iD, which allauth stores as uid."""
    # Arrange
    login = _login("orcid", uid="0000-0002-1825-0097", extra_data={"sub": "x"})
    # Act
    identity = oidc_identity_for(login)
    # Assert
    assert identity.subject == "0000-0002-1825-0097"


def test_empty_subject_is_refused():
    """An empty subject would collapse every user of an issuer into one."""
    # Arrange
    kwargs = {"issuer": "https://accounts.google.com", "subject": ""}
    # Act / guarded below
    # Assert
    with pytest.raises(ValueError):
        OidcIdentity(**kwargs)


def test_local_issuer_is_a_urn_not_a_url():
    """A local account has no external issuer, so it must not look like one."""
    # Arrange
    expected_prefix = "urn:"
    # Act
    actual = LOCAL_ISSUER
    # Assert
    assert actual.startswith(expected_prefix)


def test_every_enabled_social_provider_has_an_issuer():
    """THE GATE. Enabling a provider without an issuer fails here, in CI,
    rather than at a real user's login. Reads the live settings, so it
    tracks configuration rather than restating it."""
    # Arrange
    from django.conf import settings

    enabled = list(getattr(settings, "SOCIALACCOUNT_PROVIDERS", {}) or {})
    # Act
    unmapped = configured_providers_are_mapped(enabled)
    # Assert
    assert unmapped == [], (
        f"providers enabled in SOCIALACCOUNT_PROVIDERS with no OIDC issuer: "
        f"{unmapped}. Add them to PROVIDER_ISSUERS "
        f"(known: {sorted(PROVIDER_ISSUERS)})."
    )


# EOF
