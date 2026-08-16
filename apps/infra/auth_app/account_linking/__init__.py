#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scitex.ai account linking — one human, many providers, one board identity.

The operator's ruling (2026-08-14): identity keys on the EMAIL ADDRESS, not
the username (「ユーザ名よりはメールアドレスかな」), entry is OAuth
(「ま、oauthあれば良いんじゃないですかね」), and it must be safe for a PUBLIC
app and for MULTIPLE scitex.ai instances.

Layering — each module has one job, and the pure ones have no Django import
so they stay unit-testable without a database:

``verification``
    Is this address VERIFIED by the provider? Returns a three-valued verdict
    (verified / unverified / unknown), never a bare bool. Pure.
``providers``
    Which OIDC (issuer, subject) pair does this login carry? Pure, and
    FAIL-LOUD on a provider nobody has assigned an issuer to.
``models``
    The two durable tables. ``VerifiedEmail`` is the account KEY — a unique
    constraint, so "one address means one human" is enforced by the database
    rather than by everyone remembering it. ``LinkedIdentity`` is one row per
    provider identity pointing at that human.
``registry``
    The single seam that writes the board-side user record via the
    scitex-cards public API. The ONLY module here that knows cards exists.
``service``
    The orchestration called from the allauth adapter on every login.

WHY THE OIDC PAIR LIVES HERE AND NOT IN THE CARDS STORE
-------------------------------------------------------
The request that opened this work said the cards store models OIDC identity
as (issuer, subject). Measured against scitex_cards 0.37.1 — the latest
published version — it does not: ``users`` carries id / kind / host_at_name /
notify_json / turn_url / a2a_port / created_at / last_seen / record_json, and
``rg issuer|oidc|openid`` over the whole package returns nothing.

That is not a blocker, because the operator's actual requirement is
email-keyed identity and the cards ``user_names`` table already is exactly
that shape: ``name TEXT PRIMARY KEY`` referencing ``users(id)``, i.e. many
names collapsing onto one user, globally unique, and fail-loud on collision.
So the verified email goes in as an alias and email-keyed lookup is unique BY
CONSTRUCTION. See :mod:`.registry`.

The (issuer, subject) pair genuinely has no home over there, and it is NOT
smuggled into ``record_json`` or the opaque ``notify`` bag: an unindexed JSON
blob enforces no uniqueness, so identity stored that way only LOOKS enforced.
It stays here, in a table with a real unique constraint — which is also the
correct owner, since hub is the only component that ever speaks to the
providers. Cards never needs the pair in order to attribute a card.
"""

from .providers import (
    OidcIdentity,
    UnmappedProviderError,
    oidc_identity_for,
    provider_issuer,
)
from .verification import EmailVerdict, verified_email_of

__all__ = [
    "EmailVerdict",
    "OidcIdentity",
    "UnmappedProviderError",
    "oidc_identity_for",
    "provider_issuer",
    "verified_email_of",
]

# EOF
