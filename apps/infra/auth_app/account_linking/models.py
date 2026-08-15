#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The two durable tables behind scitex.ai account linking.

``VerifiedEmail`` is the ACCOUNT KEY and the reason this is two tables rather
than one. The operator's rule is "one verified address means one human"; a
single ``LinkedIdentity`` table could only express that as a convention every
future caller has to remember. A unique column expresses it as a fact the
database enforces, so the second provider that arrives with an
already-claimed address hits an ``IntegrityError`` instead of quietly
minting a second account.

``LinkedIdentity`` is one row per provider identity — unique on
``(issuer, subject)``, because an OIDC subject is only unique within its
issuer.

Both models are registered under the ``auth_app`` label: Django resolves a
model's app from the containing app config by module prefix, and this package
sits inside ``apps.infra.auth_app``. They are imported from
``auth_app/models.py`` so the app registry finds them.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class VerifiedEmail(models.Model):
    """A provider-verified address, and the one human it identifies.

    Only ever written for an address whose provider ASSERTED verification —
    see :mod:`..verification`. An unverified address is attacker-supplied
    and must never reach this table, because reaching it is what grants
    access to the linked account.
    """

    email = models.EmailField(
        unique=True,
        help_text=(
            "Normalised (lowercased) verified address. UNIQUE — this is the "
            "account key; the constraint is what makes 'one address, one "
            "human' true rather than merely intended."
        ),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verified_emails",
        help_text="The human this address identifies.",
    )
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "verified email"
        verbose_name_plural = "verified emails"
        indexes = [models.Index(fields=["user"])]

    def __str__(self) -> str:
        return f"{self.email} -> {self.user}"


class LinkedIdentity(models.Model):
    """One provider identity ``(issuer, subject)`` linked to one hub user.

    A human with a Google login and an ORCID login has two rows here and one
    row in :class:`VerifiedEmail` — that fan-in is the whole point of
    "account linking".
    """

    issuer = models.CharField(
        max_length=255,
        help_text=(
            "OIDC issuer, e.g. https://accounts.google.com. An IDENTITY KEY: "
            "changing a stored value re-keys the row and splits the user."
        ),
    )
    subject = models.CharField(
        max_length=255,
        help_text="OIDC subject ('sub'), unique only within its issuer.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="linked_identities",
    )
    verified_email = models.ForeignKey(
        VerifiedEmail,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="identities",
        help_text=(
            "The verified address this login carried, when it carried one. "
            "NULL is a real state, not a gap: ORCID commonly returns no "
            "email at all, and such a login is still a valid identity — it "
            "just cannot be used to key or link an account."
        ),
    )
    cards_user_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text=(
            "The 'u_*' id of this human's record in the scitex-cards user "
            "registry. Blank until the board-side upsert succeeds; the write "
            "is deliberately allowed to fail without failing the login."
        ),
    )
    host_at_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "Instance namespacing ('host@name'), so two scitex.ai instances "
            "sharing a cards store do not collide."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "linked identity"
        verbose_name_plural = "linked identities"
        constraints = [
            models.UniqueConstraint(
                fields=["issuer", "subject"],
                name="uniq_linked_identity_issuer_subject",
            )
        ]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["cards_user_id"]),
        ]

    @property
    def deterministic_cards_id(self) -> str:
        """The cards user id this identity WOULD mint, fleet-wide.

        DERIVED, not stored, and deliberately so. It is a pure function of
        ``issuer`` and ``subject``, both of which are already columns on this
        row; a third column holding their digest would be denormalised state
        that can drift from its own definition after a data fix.

        Not yet authoritative — ``scitex_cards.register_user`` mints ids
        internally with ``secrets.token_hex`` and accepts no caller-supplied
        id, so :attr:`cards_user_id` still holds a random one. When that API
        lands, this becomes the value hub sends, and existing rows can be
        backfilled by comparing the two. See card
        ``cards-email-uniqueness-is-fleet-wide-not-per-host-20260814``.
        """
        from .providers import OidcIdentity, deterministic_cards_user_id

        return deterministic_cards_user_id(
            OidcIdentity(issuer=self.issuer, subject=self.subject)
        )

    def __str__(self) -> str:
        return f"{self.issuer}#{self.subject} -> {self.user}"


__all__ = ["LinkedIdentity", "VerifiedEmail"]

# EOF
