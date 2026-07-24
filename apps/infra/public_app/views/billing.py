#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: ./apps/infra/public_app/views/billing.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/infra/public_app/views/billing.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Stripe billing scaffold (no entitlement logic — see card
hub-billing-entitlement-minimal for that follow-up).

Surfaces:

- ``billing_checkout`` — POST; creates a Stripe Checkout Session from a
  configured plan's ``stripe_price_id``. STAFF-ONLY while testing
  (operator directive 2026-07-08): only staff/superuser may reach it.
- ``stripe_webhook``  — POST; CSRF-exempt but SIGNATURE-VERIFIED
  (Stripe-Signature v1 scheme, hand-verified with HMAC-SHA256 +
  constant-time compare + timestamp tolerance). Records events to the
  minimal ``BillingEvent`` model.

Fail-loud contract (no silent fallback): while
``SCITEX_HUB_STRIPE_SECRET_KEY`` / ``SCITEX_HUB_STRIPE_WEBHOOK_SECRET``
are unconfigured, both endpoints return an explicit 503 with an
explanation instead of pretending to work. Secrets come only from the
environment and are never logged or echoed in responses.
"""

import hashlib
import hmac
import json
import time

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# Max allowed age (seconds) of a webhook signature timestamp — mirrors
# stripe-python's DEFAULT_TOLERANCE. Prevents replay of captured payloads.
STRIPE_SIGNATURE_TOLERANCE_SECONDS = 300


def _service_unavailable(reason: str) -> JsonResponse:
    """Explicit 503 — billing is scaffolded but not configured."""
    return JsonResponse(
        {
            "error": "billing_not_configured",
            "detail": reason,
        },
        status=503,
    )


def verify_stripe_signature(
    payload: bytes,
    signature_header: str,
    secret: str,
    tolerance_seconds: int = STRIPE_SIGNATURE_TOLERANCE_SECONDS,
) -> bool:
    """Verify a ``Stripe-Signature`` header against the raw payload.

    Implements Stripe's documented scheme: the header carries
    ``t=<unix-ts>,v1=<hex>`` items; the expected signature is
    ``HMAC_SHA256(secret, f"{t}.{payload}")``. Comparison is
    constant-time and the timestamp must be within ``tolerance_seconds``
    of now (replay protection).
    """
    if not signature_header or not secret:
        return False

    timestamp = None
    candidate_signatures = []
    for item in signature_header.split(","):
        key, _, value = item.strip().partition("=")
        if key == "t":
            timestamp = value
        elif key == "v1":
            candidate_signatures.append(value)

    if timestamp is None or not candidate_signatures:
        return False
    try:
        timestamp_int = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - timestamp_int) > tolerance_seconds:
        return False

    signed_payload = timestamp.encode() + b"." + payload
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return any(
        hmac.compare_digest(expected, candidate)
        for candidate in candidate_signatures
    )


@require_POST
def billing_checkout(request):
    """Create a Stripe Checkout Session for a configured plan.

    Staff-only while testing (operator directive): non-staff callers get
    403. Requires POST field ``price_id`` matching the
    ``stripe_price_id`` of a configured plan in
    ``SCITEX_HUB_BILLING_PLANS`` — arbitrary price ids are rejected.
    """
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse(
            {
                "error": "forbidden",
                "detail": (
                    "Checkout is operator-only while billing is in "
                    "testing. Contact support@scitex.ai."
                ),
            },
            status=403,
        )

    if not settings.STRIPE_SECRET_KEY:
        return _service_unavailable(
            "SCITEX_HUB_STRIPE_SECRET_KEY is not configured. Checkout is "
            "disabled until Stripe keys are set in the environment "
            "(SECRET/.env.*)."
        )

    plans = settings.BILLING_PLANS
    if not plans:
        return _service_unavailable(
            "SCITEX_HUB_BILLING_PLANS is empty — no purchasable plans are "
            "configured yet (有料プランは準備中です)."
        )

    price_id = request.POST.get("price_id", "")
    plan = next((p for p in plans if p["stripe_price_id"] == price_id), None)
    if plan is None:
        return JsonResponse(
            {
                "error": "unknown_price_id",
                "detail": "price_id does not match any configured plan.",
            },
            status=400,
        )

    try:
        import stripe
    except ImportError:
        return _service_unavailable(
            "The 'stripe' package is not installed in this environment. "
            "Install project dependencies (pip install -e '.[all]')."
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY
    mode = "payment" if plan["interval"] == "once" else "subscription"
    session = stripe.checkout.Session.create(
        mode=mode,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=request.build_absolute_uri("/pricing/?checkout=success"),
        cancel_url=request.build_absolute_uri("/pricing/?checkout=cancelled"),
    )
    return redirect(session.url)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Stripe webhook endpoint — signature-verified event recorder.

    CSRF-exempt (Stripe cannot send a CSRF token) but every request must
    carry a valid ``Stripe-Signature`` header. Verified events are
    persisted to ``BillingEvent`` (idempotent on the Stripe event id).
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        return _service_unavailable(
            "SCITEX_HUB_STRIPE_WEBHOOK_SECRET is not configured. The "
            "webhook is disabled until the signing secret is set in the "
            "environment (SECRET/.env.*)."
        )

    payload = request.body
    signature_header = request.headers.get("Stripe-Signature", "")
    if not verify_stripe_signature(
        payload, signature_header, settings.STRIPE_WEBHOOK_SECRET
    ):
        return JsonResponse(
            {
                "error": "invalid_signature",
                "detail": "Stripe-Signature verification failed.",
            },
            status=400,
        )

    try:
        event = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse(
            {"error": "invalid_payload", "detail": "Body is not valid JSON."},
            status=400,
        )

    event_id = event.get("id", "")
    event_type = event.get("type", "")
    if not event_id or not event_type:
        return JsonResponse(
            {
                "error": "invalid_event",
                "detail": "Event must carry 'id' and 'type'.",
            },
            status=400,
        )

    from ..models import BillingEvent

    _, created = BillingEvent.objects.get_or_create(
        event_id=event_id,
        defaults={"event_type": event_type, "payload": event},
    )
    return JsonResponse({"received": True, "created": created})


# EOF
