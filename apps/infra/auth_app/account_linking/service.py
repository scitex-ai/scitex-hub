#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orchestration: turn a completed login into durable linked identity.

Called from the allauth adapter on every login. Three steps, in this order,
because each one depends on the previous having fail-closed correctly:

1. Decide whether the login carried a VERIFIED address (:mod:`.verification`).
2. Claim or confirm that address as this user's account key
   (:class:`~.models.VerifiedEmail`), and record the provider identity
   (:class:`~.models.LinkedIdentity`).
3. Mirror the human into the board's user registry (:mod:`.registry`).

Step 3 is allowed to fail without failing the login; steps 1 and 2 are not.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings
from django.db import IntegrityError, transaction

from .models import LinkedIdentity, VerifiedEmail
from .providers import local_identity_for, oidc_identity_for
from .verification import verified_email_of

logger = logging.getLogger(__name__)

#: Link outcomes — a declared state per call, never a bare bool.
LINKED = "linked"
NO_VERIFIED_EMAIL = "no-verified-email"
EMAIL_OWNED_BY_ANOTHER_USER = "email-owned-by-another-user"

VALID_LINK_STATUSES: tuple[str, ...] = (
    LINKED,
    NO_VERIFIED_EMAIL,
    EMAIL_OWNED_BY_ANOTHER_USER,
)


@dataclass(frozen=True)
class LinkResult:
    """Fixed-shape result of linking one login.

    Attributes
    ----------
    status : str
        One of :data:`VALID_LINK_STATUSES`. ``no-verified-email`` is a
        SUCCESS state for the login — an ORCID account with no address is
        perfectly valid, it simply cannot be email-keyed.
    identity : LinkedIdentity | None
        The stored provider-identity row, when one was written.
    email : str | None
        The verified address, when the login carried one.
    cards_status : str | None
        The board-side upsert status (see :mod:`.registry`), or ``None``
        when no board write was attempted.
    """

    status: str
    identity: "LinkedIdentity | None" = None
    email: str | None = None
    cards_status: str | None = None

    def __post_init__(self) -> None:
        if self.status not in VALID_LINK_STATUSES:
            raise ValueError(
                f"invalid link status {self.status!r}; must be one of "
                f"{VALID_LINK_STATUSES}"
            )


def instance_host_at_name() -> str:
    """This instance's ``host@name`` for cards-side namespacing.

    Reads ``SCITEX_INSTANCE_NAME`` from settings. Several scitex.ai
    instances share a synchronised cards store, so records need to say which
    instance minted them.
    """
    return str(getattr(settings, "SCITEX_INSTANCE_NAME", "") or "").strip()


def _claim_verified_email(user, email: str) -> "VerifiedEmail | None":
    """Claim ``email`` for ``user``; ``None`` when another user holds it.

    The unique constraint on ``VerifiedEmail.email`` is the real gate here.
    ``get_or_create`` still races — two concurrent logins can both miss the
    SELECT and both INSERT — so the ``IntegrityError`` is caught and
    re-resolved rather than assumed impossible. That is the difference
    between a constraint that protects the data and one that merely produces
    a 500 under load.
    """
    try:
        with transaction.atomic():
            row, _created = VerifiedEmail.objects.get_or_create(
                email=email, defaults={"user": user}
            )
    except IntegrityError:
        row = VerifiedEmail.objects.filter(email=email).first()
        if row is None:
            raise

    if row.user_id != user.pk:
        logger.error(
            "[account-linking] REFUSING to link %s to user %s: the address is "
            "already the account key of user %s. This is either a genuine "
            "conflict needing a human, or an attempted takeover.",
            email,
            user.pk,
            row.user_id,
        )
        return None

    # auto_now keeps last_seen honest for a returning user.
    row.save(update_fields=["last_seen"])
    return row


def _record_identity(user, identity, verified_email) -> LinkedIdentity:
    """Upsert the ``(issuer, subject)`` row and point it at ``user``.

    The unique key is ``(issuer, subject)``, so a provider identity that
    arrives attached to a DIFFERENT user re-points to the current one. That
    is correct rather than alarming: it is what happens when a human merges
    accounts, and the address-level takeover check has already run above.
    """
    row, _created = LinkedIdentity.objects.update_or_create(
        issuer=identity.issuer,
        subject=identity.subject,
        defaults={
            "user": user,
            "verified_email": verified_email,
            "host_at_name": instance_host_at_name(),
        },
    )
    return row


def _mirror_to_cards(row: LinkedIdentity, user, email: str) -> str:
    """Write the human into the cards registry; return the upsert status.

    Never raises — :func:`~.registry.upsert_cards_user` returns a declared
    status for every failure mode, and a board outage must not break a
    login.
    """
    from .registry import upsert_cards_user

    display_name = (user.get_username() or "").strip()
    result = upsert_cards_user(
        email=email,
        display_name=display_name,
        host_at_name=instance_host_at_name(),
    )
    if result.cards_user_id and row.cards_user_id != result.cards_user_id:
        row.cards_user_id = result.cards_user_id
        row.save(update_fields=["cards_user_id"])
    return result.status


def link_identity(user, identity, verdict) -> LinkResult:
    """Link one already-derived identity + email verdict to ``user``.

    The shared core of :func:`link_social_login` and
    :func:`link_local_login`; separated so both entry points cannot drift
    into different rules about what "verified" means.
    """
    verified_email = None
    email = None

    if verdict.is_account_key:
        email = verdict.email
        verified_email = _claim_verified_email(user, email)
        if verified_email is None:
            return LinkResult(
                status=EMAIL_OWNED_BY_ANOTHER_USER,
                email=email,
            )

    row = _record_identity(user, identity, verified_email)

    if email is None:
        # A valid identity with no email-keyable address (ORCID commonly).
        # Recorded, but never mirrored: the board's key IS the address.
        return LinkResult(status=NO_VERIFIED_EMAIL, identity=row)

    cards_status = _mirror_to_cards(row, user, email)
    return LinkResult(
        status=LINKED,
        identity=row,
        email=email,
        cards_status=cards_status,
    )


def link_social_login(user, sociallogin) -> LinkResult:
    """Link a completed allauth social login.

    Raises
    ------
    UnmappedProviderError
        When the provider has no issuer mapping — deliberately loud; see
        :mod:`.providers`.
    """
    return link_identity(
        user,
        oidc_identity_for(sociallogin),
        verified_email_of(sociallogin),
    )


def link_local_login(user) -> LinkResult:
    """Link a local email+password account.

    The address only counts when allauth has an ``EmailAddress`` row marked
    verified — a self-asserted ``User.email`` is not a verification, and
    treating it as one would reopen the same takeover hole from the local
    signup side.
    """
    from allauth.account.models import EmailAddress

    from .verification import EmailVerdict, UNKNOWN, VERIFIED, normalize_email

    address = (
        EmailAddress.objects.filter(user=user, verified=True)
        .order_by("-primary", "pk")
        .first()
    )
    if address is None:
        verdict = EmailVerdict(
            email=None, status=UNKNOWN, source="allauth.EmailAddress(verified)"
        )
    else:
        verdict = EmailVerdict(
            email=normalize_email(address.email),
            status=VERIFIED,
            source="allauth.EmailAddress(verified)",
        )
    return link_identity(user, local_identity_for(user), verdict)


__all__ = [
    "EMAIL_OWNED_BY_ANOTHER_USER",
    "LINKED",
    "NO_VERIFIED_EMAIL",
    "VALID_LINK_STATUSES",
    "LinkResult",
    "instance_host_at_name",
    "link_identity",
    "link_local_login",
    "link_social_login",
]

# EOF
