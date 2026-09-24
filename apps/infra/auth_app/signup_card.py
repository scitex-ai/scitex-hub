#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot signup: account fields + card on a single page.

The signup form collects username/email/password AND the card in one submit.
Under the hood it is still two ordered operations — the account must exist
before Stripe can own a customer for it — but the browser drives both from
one page with one button:

1. ``POST /auth/signup/`` (AJAX) creates the inactive user, sends the OTP,
   mints a SetupIntent for that user, and returns the client secret plus a
   single-purpose signed token binding the user to that intent.
2. Stripe.js confirms the card browser-to-Stripe (Elements live-validates
   number/expiry/CVC; the bank verifies at confirm; the server refuses a
   ``cvc_check == fail`` card at verify time).
3. ``POST /billing/confirm-card/`` with the token verifies the intent
   (succeeded + bound to this user) and persists the card via the SAME
   ``apply_setup_completed`` path the webhook uses.
4. The browser lands on the email-verification page. Verification still
   gates activation; a verified account that already holds a usable card
   skips the payment step (see ``mark_verified``).

The token is the only thing that lets an unauthenticated caller touch the
confirm endpoint, and it authorises exactly one intent for exactly one user
for 30 minutes. No session, no login of an unverified account.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

SIGNUP_CARD_TOKEN_SALT = "signup-card-v1"
SIGNUP_CARD_TOKEN_MAX_AGE = 30 * 60


def mint_signup_card_token(user, setup_intent_id: str) -> str:
    """Single-purpose token binding ``user`` to ``setup_intent_id``."""
    from django.core.signing import TimestampSigner

    signer = TimestampSigner(salt=SIGNUP_CARD_TOKEN_SALT)
    return signer.sign_object({"u": user.pk, "s": setup_intent_id or ""})


def resolve_signup_card_token(token: str):
    """Return ``(user, setup_intent_id)`` or ``(None, None)`` when bad."""
    if not token:
        return None, None
    from django.contrib.auth.models import User
    from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

    try:
        signer = TimestampSigner(salt=SIGNUP_CARD_TOKEN_SALT)
        payload = signer.unsign_object(token, max_age=SIGNUP_CARD_TOKEN_MAX_AGE)
        user = User.objects.filter(pk=payload.get("u")).first()
        if user is None or not payload.get("s"):
            return None, None
        return user, payload["s"]
    except (BadSignature, SignatureExpired, Exception):
        logger.info("Rejected bad/expired signup-card token")
        return None, None


def mint_signup_setup_intent(user) -> dict:
    """SetupIntent for a just-created signup user, or ``{"open": False}``.

    The funnel plan resolver needs no onboarding authority (it falls back to
    the single allowlisted plan); the authority is still created at
    verification time only, so an unverified signup never looks verified to
    ``payment_required``. ``open: False`` keeps the page to account-only
    on deployments without Stripe keys — the payment step stays the fallback.
    """
    from apps.infra.accounts_app.payment_step import funnel_plan
    from apps.infra.public_app.services.billing_provider import (
        BillingNotConfigured,
        BillingOperationRefused,
        get_billing_provider,
        inline_card_form_info,
    )

    info = inline_card_form_info()
    if not info.get("open"):
        return {"open": False}
    row = funnel_plan(user, requested_id=None)
    if row is None:
        return {"open": False}
    try:
        provider = get_billing_provider()
        setup_intent_id, client_secret = provider.create_setup_intent(
            user, pricing_id=row["id"]
        )
    except (BillingNotConfigured, BillingOperationRefused) as exc:
        logger.info("Signup card intent unavailable: %s", exc)
        return {"open": False}
    if not client_secret:
        return {"open": False}
    return {
        "open": True,
        "setup_intent_id": setup_intent_id,
        "client_secret": client_secret,
        "publishable_key": info.get("publishable_key", ""),
        "plan_label": row.get("label") or row.get("name") or "",
        "monthly_usd": float(row.get("amount") or 0),
        "signup_token": mint_signup_card_token(user, setup_intent_id),
    }


# EOF
