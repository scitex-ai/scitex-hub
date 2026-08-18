#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run account linking on every login — not only on signup.

Hooked to allauth's ``user_logged_in``, which fires for social AND local
logins and carries ``sociallogin`` only for the former. Signup-time hooks
(``save_user``) would link a user once and then never again, so a human who
signed up before this shipped would stay invisible to the board forever.

A failure here must not cost the user their session: they have already
authenticated, and refusing to complete a login because a bookkeeping write
failed would turn a board problem into an outage. So the receiver logs loudly
and returns. The one thing it does NOT swallow is the unmapped-provider
error, which is a configuration fault that must be fixed rather than
tolerated — see :mod:`.providers`.
"""

from __future__ import annotations

import logging

from allauth.account.signals import user_logged_in
from django.dispatch import receiver

from .providers import UnmappedProviderError
from .service import (
    EMAIL_OWNED_BY_ANOTHER_USER,
    link_local_login,
    link_social_login,
)

logger = logging.getLogger(__name__)


@receiver(user_logged_in, dispatch_uid="account_linking_on_login")
def link_on_login(sender, request, user, **kwargs):
    """Record this login's identity and mirror the human onto the board."""
    sociallogin = kwargs.get("sociallogin")
    try:
        if sociallogin is not None:
            result = link_social_login(user, sociallogin)
        else:
            result = link_local_login(user)
    except UnmappedProviderError:
        # Deliberately NOT swallowed beyond this log: a provider with no
        # issuer cannot be given a stable identity, and inventing one would
        # split the user in two later. Loud, actionable, and it does not
        # touch the session.
        logger.exception(
            "[account-linking] login by user %s used a provider with no OIDC "
            "issuer mapping; no identity was recorded",
            user.pk,
        )
        return
    except Exception:  # noqa: BLE001 - see module docstring
        logger.exception(
            "[account-linking] failed to record identity for user %s; the "
            "login itself succeeded",
            user.pk,
        )
        return

    if result.status == EMAIL_OWNED_BY_ANOTHER_USER:
        logger.error(
            "[account-linking] user %s logged in with address %s, which is "
            "the account key of a DIFFERENT user. No link was made. Needs a "
            "human decision.",
            user.pk,
            result.email,
        )
        return

    logger.info(
        "[account-linking] user %s login linked: status=%s cards=%s",
        user.pk,
        result.status,
        result.cards_status,
    )


__all__ = ["link_on_login"]

# EOF
