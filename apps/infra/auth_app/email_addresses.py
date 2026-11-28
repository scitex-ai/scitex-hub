"""One answer to "has this account proven its e-mail address?".

The hub's own signup proves an address with a one-time code
(``EmailVerification``) and allauth proves one with a confirmation link or a
provider's verified claim (``allauth.account.models.EmailAddress``). allauth
only reads its own table, so every code-based proof is also written there as
a verified ``EmailAddress``. Readers ask :func:`is_verified`.
"""

from __future__ import annotations

import logging

from allauth.account.models import EmailAddress
from django.db import IntegrityError, transaction

logger = logging.getLogger(__name__)


def is_verified(user, email: str | None = None) -> bool:
    """True when ``email`` (default: the account's own) is verified for ``user``."""
    address = (email if email is not None else getattr(user, "email", "")) or ""
    if not address or getattr(user, "pk", None) is None:
        return False
    return EmailAddress.objects.filter(
        user=user, email__iexact=address, verified=True
    ).exists()


def prompt_verification(request, user) -> bool:
    """Send a confirmation link to a signed-in account whose address is unproven.

    The gentle path for accounts created before verification was mandatory:
    they keep their session and are asked to confirm, rather than being
    refused. allauth rate-limits the mail per address and adds the on-page
    message. A mail failure never breaks the sign-in. Returns True if sent.
    """
    if not getattr(user, "email", "") or is_verified(user):
        return False
    from allauth.account.internal.flows.email_verification import (
        send_verification_email_for_user,
    )

    try:
        return bool(send_verification_email_for_user(request, user))
    except Exception:
        logger.exception("Could not send an address confirmation to user %s", user.pk)
        return False


def record_verified(user, email: str) -> EmailAddress | None:
    """Record that ``user`` proved ``email`` and make it the primary address.

    Idempotent; case variants of the address are folded into one row. Returns
    ``None`` (and logs) when another account already holds the address as
    verified, which the database refuses; the caller's own flow still
    completes.
    """
    address = email.strip().lower()
    try:
        with transaction.atomic():
            rows = list(EmailAddress.objects.filter(user=user, email__iexact=address))
            keep = rows[0] if rows else EmailAddress(user=user, email=address)
            for extra in rows[1:]:
                extra.delete()
            others = EmailAddress.objects.filter(user=user, primary=True)
            if keep.pk is not None:
                others = others.exclude(pk=keep.pk)
            others.update(primary=False)
            keep.email = address
            keep.verified = True
            keep.primary = True
            keep.save()
            return keep
    except IntegrityError:
        logger.warning(
            "Could not record %s as verified for user %s: the address is "
            "already verified on another account.",
            address,
            user.pk,
        )
        return None
