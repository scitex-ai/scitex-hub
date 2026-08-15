#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The fleet-wide cards user id: same human, same id, on every host.

The fleet runs one PostgreSQL per host, synchronised between them, and any
machine can join. A randomly minted user id therefore differs per host for
the same person and has to be merged after the fact. Deriving it from the
provider identity makes every host agree with zero coordination — the
property agreed on card
``cards-email-uniqueness-is-fleet-wide-not-per-host-20260814``.

The ambiguity test is the one that matters. A naive ``f"{issuer}|{subject}"``
would let two DIFFERENT identities hash to one id, silently merging two
people — the same joined-string collision class hub argued against upstream,
which is why the payload here is length-prefixed.
"""

from apps.infra.auth_app.account_linking.providers import (
    CARDS_USER_ID_PREFIX,
    OidcIdentity,
    deterministic_cards_user_id,
)

GOOGLE = "https://accounts.google.com"


def test_the_same_identity_always_yields_the_same_id():
    """The whole point: two hosts, no coordination, one id."""
    # Arrange
    identity = OidcIdentity(issuer=GOOGLE, subject="sub-42")
    # Act
    first, second = (
        deterministic_cards_user_id(identity),
        deterministic_cards_user_id(OidcIdentity(issuer=GOOGLE, subject="sub-42")),
    )
    # Assert
    assert first == second


def test_different_subjects_yield_different_ids():
    # Arrange
    alice = OidcIdentity(issuer=GOOGLE, subject="sub-alice")
    bob = OidcIdentity(issuer=GOOGLE, subject="sub-bob")
    # Act
    ids = {deterministic_cards_user_id(alice), deterministic_cards_user_id(bob)}
    # Assert
    assert len(ids) == 2


def test_the_same_subject_under_different_issuers_yields_different_ids():
    """A subject is unique only WITHIN its issuer."""
    # Arrange
    google = OidcIdentity(issuer=GOOGLE, subject="collide")
    orcid = OidcIdentity(issuer="https://orcid.org", subject="collide")
    # Act
    ids = {deterministic_cards_user_id(google), deterministic_cards_user_id(orcid)}
    # Assert
    assert len(ids) == 2


def test_separator_ambiguity_cannot_merge_two_people():
    """THE COLLISION TEST.

    Under a naive f"{issuer}|{subject}" both of these render the identical
    string "https://x|a|b" and hash to ONE id — two different people sharing
    one board identity. Length-prefixing is what makes that inexpressible.
    """
    # Arrange
    left = OidcIdentity(issuer="https://x", subject="a|b")
    right = OidcIdentity(issuer="https://x|a", subject="b")
    # Act
    ids = {deterministic_cards_user_id(left), deterministic_cards_user_id(right)}
    # Assert
    assert len(ids) == 2


def test_the_id_looks_like_a_cards_user_id():
    """Shape must match scitex-cards' own u_ + 12 hex, or it is not a drop-in."""
    # Arrange
    identity = OidcIdentity(issuer=GOOGLE, subject="sub-42")
    # Act
    user_id = deterministic_cards_user_id(identity)
    # Assert
    assert len(user_id) == len(CARDS_USER_ID_PREFIX) + 12


def test_the_id_is_hex_after_the_prefix():
    # Arrange
    identity = OidcIdentity(issuer=GOOGLE, subject="sub-42")
    # Act
    body = deterministic_cards_user_id(identity)[len(CARDS_USER_ID_PREFIX):]
    # Assert
    assert all(char in "0123456789abcdef" for char in body)


# EOF
