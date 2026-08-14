#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which OIDC ``(issuer, subject)`` pair does this login carry?

An OIDC subject is only unique WITHIN its issuer, so the pair is the atom of
provider identity — never the subject alone. Google's ``sub`` and an ORCID
iD could in principle collide as strings; scoped by issuer they cannot.

PURE — no Django, no database, no network.

WHY AN UNMAPPED PROVIDER RAISES
-------------------------------
It would be friendlier to invent an issuer for a provider nobody has mapped
(``urn:scitex:provider:<name>``) and carry on. That friendliness is a trap:
the invented value is stored, and the day someone supplies the provider's
REAL issuer, every existing row keys off the old string. One human silently
becomes two accounts, and the split shows up as "my cards disappeared"
rather than as an error anyone can trace.

So an unmapped provider fails loud, at login, naming the file and the line to
edit. The blast radius is one provider that nobody has finished configuring,
and :func:`configured_providers_are_mapped` lets the test suite catch it
before a user ever does — a mechanical barrier instead of a comment asking
people to remember.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Provider id (allauth's ``SocialAccount.provider``) -> OIDC issuer.
#:
#: Values are the issuers the providers themselves publish in their discovery
#: documents, and they are IDENTITY KEYS: changing a value here re-keys every
#: stored row for that provider and splits existing users in two. Add rows;
#: do not edit them without a migration that rewrites the stored issuers.
PROVIDER_ISSUERS: dict[str, str] = {
    # https://accounts.google.com/.well-known/openid-configuration
    "google": "https://accounts.google.com",
    # https://orcid.org/.well-known/openid-configuration
    "orcid": "https://orcid.org",
}

#: Issuer for accounts created by local email+password signup rather than by
#: an external provider. Not an OIDC issuer — a local account has no external
#: one — so it is a URN in our own namespace, which cannot be confused with a
#: real issuer URL and cannot ever be "corrected" to one later.
LOCAL_ISSUER = "urn:scitex:local"

#: Provider ids whose subject is the ORCID iD rather than an OIDC ``sub``.
#: ORCID's iD IS its stable subject, and allauth stores it as the account uid.
_ORCID_PROVIDERS = frozenset({"orcid"})


class UnmappedProviderError(ValueError):
    """Raised for a social provider with no issuer in :data:`PROVIDER_ISSUERS`.

    Carries the offending provider id and the exact edit that fixes it, per
    the fail-loud-with-an-actionable-hint convention.
    """


@dataclass(frozen=True)
class OidcIdentity:
    """A provider identity: the ``(issuer, subject)`` pair, both non-empty."""

    issuer: str
    subject: str

    def __post_init__(self) -> None:
        if not (isinstance(self.issuer, str) and self.issuer.strip()):
            raise ValueError(
                f"OidcIdentity.issuer must be a non-empty string "
                f"(got {self.issuer!r})"
            )
        if not (isinstance(self.subject, str) and self.subject.strip()):
            raise ValueError(
                f"OidcIdentity.subject must be a non-empty string "
                f"(got {self.subject!r}); an empty subject would collapse "
                f"every user of issuer {self.issuer!r} onto one identity"
            )


def provider_issuer(provider: str) -> str:
    """Issuer URL for an allauth provider id, or raise.

    Raises
    ------
    UnmappedProviderError
        When ``provider`` has no entry in :data:`PROVIDER_ISSUERS`.
    """
    if not (isinstance(provider, str) and provider.strip()):
        raise UnmappedProviderError(
            f"provider must be a non-empty string (got {provider!r})"
        )
    key = provider.strip().lower()
    issuer = PROVIDER_ISSUERS.get(key)
    if issuer is None:
        raise UnmappedProviderError(
            f"social provider {key!r} has no OIDC issuer mapping, so its "
            f"logins cannot be given a stable identity. Add it to "
            f"PROVIDER_ISSUERS in "
            f"apps/infra/auth_app/account_linking/providers.py using the "
            f"issuer from that provider's "
            f"/.well-known/openid-configuration. Known providers: "
            f"{sorted(PROVIDER_ISSUERS)}"
        )
    return issuer


def _subject_of(provider: str, account) -> str:
    """Stable subject for this provider's account record.

    ORCID's stable subject is the iD, which allauth stores as the account
    ``uid``. For OIDC providers the ``sub`` claim is authoritative and the
    ``uid`` mirrors it — prefer the claim, fall back to ``uid``, because a
    provider that omits ``sub`` from ``extra_data`` still populated ``uid``
    during the token exchange.
    """
    uid = getattr(account, "uid", None)
    if provider in _ORCID_PROVIDERS:
        return str(uid or "").strip()

    extra = getattr(account, "extra_data", None)
    if isinstance(extra, dict):
        sub = extra.get("sub")
        if isinstance(sub, str) and sub.strip():
            return sub.strip()
    return str(uid or "").strip()


def oidc_identity_for(sociallogin) -> OidcIdentity:
    """``(issuer, subject)`` for an allauth ``SocialLogin``.

    Raises
    ------
    UnmappedProviderError
        When the login's provider has no issuer mapping.
    ValueError
        When the provider supplied no usable subject — refusing beats
        storing an empty subject that would collapse every user of that
        issuer onto a single identity.
    """
    account = getattr(sociallogin, "account", None)
    provider = str(getattr(account, "provider", "") or "").strip().lower()
    issuer = provider_issuer(provider)
    return OidcIdentity(issuer=issuer, subject=_subject_of(provider, account))


def local_identity_for(user) -> OidcIdentity:
    """Identity for a local email+password account.

    The subject is the Django primary key: stable for the account's life,
    never reused, and already the thing every other hub table points at.
    """
    pk = getattr(user, "pk", None)
    if pk is None:
        raise ValueError(
            "cannot build a local identity for an unsaved user (pk is None)"
        )
    return OidcIdentity(issuer=LOCAL_ISSUER, subject=str(pk))


def configured_providers_are_mapped(provider_ids) -> list[str]:
    """Provider ids that are enabled but have no issuer — empty means fine.

    The mechanical barrier behind this module's fail-loud choice: a test
    feeds it the providers the settings actually enable, so enabling one
    without assigning an issuer fails in CI instead of at a user's login.
    """
    return sorted(
        {
            str(pid).strip().lower()
            for pid in provider_ids or ()
            if str(pid).strip().lower() not in PROVIDER_ISSUERS
        }
    )


__all__ = [
    "LOCAL_ISSUER",
    "PROVIDER_ISSUERS",
    "OidcIdentity",
    "UnmappedProviderError",
    "configured_providers_are_mapped",
    "local_identity_for",
    "oidc_identity_for",
    "provider_issuer",
]

# EOF
