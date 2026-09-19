#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: ./apps/infra/public_app/views/billing.py
# ----------------------------------------
from __future__ import annotations

import os

from config import branding

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
  minimal ``BillingEvent`` model, then lets the provider apply them.
- ``start_card_setup`` / ``start_subscription`` / ``cancel_subscription`` /
  ``open_billing_portal`` — user-facing POSTs, all through the provider-neutral
  ``get_billing_provider()`` (services/billing_provider.py).

Fail-loud contract (no silent fallback): while
``SCITEX_HUB_STRIPE_SECRET_KEY`` / ``SCITEX_HUB_STRIPE_WEBHOOK_SECRET``
are unconfigured, both endpoints return an explicit 503 with an
explanation instead of pretending to work. Secrets come only from the
environment and are never logged or echoed in responses.
"""

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..services.billing_provider import (
    BillingNotConfigured,
    BillingOperationRefused,
    get_billing_provider,
)
from ..services.stripe_provider import (  # noqa: F401  (re-exported for callers)
    STRIPE_SIGNATURE_TOLERANCE_SECONDS,
    verify_stripe_signature,
)

logger = logging.getLogger("scitex")


def _service_unavailable(reason: str) -> JsonResponse:
    """Explicit 503 — billing is scaffolded but not configured."""
    return JsonResponse(
        {
            "error": "billing_not_configured",
            "detail": reason,
        },
        status=503,
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
                    f"testing. Contact {branding.CONTACT_EMAIL}."
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
    """Billing-provider webhook: verified, deduplicated, then applied ONCE.

    CSRF-exempt (the provider cannot send a CSRF token), so the signature is
    the only authentication. Three separate gates, in order, and each one closes
    a distinct hole:

    1. SIGNATURE — the payload is genuine (unchanged).
    2. TEST/LIVE CONSISTENCY — the event's ``livemode`` must agree with the
       configured key (PR #934 review, blocker 5). A live event delivered to a
       test-configured deployment is a misconfiguration or a replay, and applying
       it would move real entitlement from a test-signed payload.
    3. IDEMPOTENT PROCESSING — the event is recorded, then CLAIMED atomically,
       applied, and marked done (blocker 6). A retry of an applied event is
       acknowledged without re-applying it; a retry of a FAILED event is allowed
       through, because that is what retrying is for.
    """
    provider = get_billing_provider()
    try:
        event = provider.verify_webhook(request.body, request.headers)
    except BillingNotConfigured as exc:
        return _service_unavailable(str(exc))
    except (UnicodeDecodeError, ValueError):
        return JsonResponse(
            {"error": "invalid_payload", "detail": "Body is not valid JSON."},
            status=400,
        )
    if event is None:
        return JsonResponse(
            {
                "error": "invalid_signature",
                "detail": "Webhook signature verification failed.",
            },
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

    from ..services import webhook_processing
    from ..services.billing_provider import event_matches_key_environment

    if not event_matches_key_environment(event, settings.STRIPE_SECRET_KEY):
        # Recorded for the operator, then refused: this event must never touch
        # entitlement, and "why did nothing happen?" needs an answer in the data.
        row, _ = webhook_processing.record_event(event)
        webhook_processing.release_event(
            "livemode does not match the configured Stripe key", row=row
        )
        logger.error(
            "Refusing webhook %s: livemode=%r does not match the configured key",
            event_id,
            event.get("livemode"),
        )
        return JsonResponse(
            {
                "error": "mode_mismatch",
                "detail": (
                    "This event's livemode does not match the configured Stripe "
                    "key; it was recorded and not applied."
                ),
            },
            status=400,
        )

    row, created = webhook_processing.record_event(event)
    claimed = webhook_processing.claim_event(event_id)
    if claimed is None:
        # Already applied, or another worker holds a live claim. Both are a
        # successful delivery from the provider's point of view: answering
        # non-2xx here would make Stripe retry an event we have already handled.
        return JsonResponse(
            {
                "received": True,
                "created": created,
                "processed": False,
                "status": row.status,
            }
        )

    try:
        provider.handle_event(event)
    except Exception as exc:
        webhook_processing.release_event(exc, row=claimed)
        logger.exception("Webhook %s failed; left claimable for retry", event_id)
        raise
    webhook_processing.complete_event(row=claimed)
    return JsonResponse(
        {
            "received": True,
            "created": created,
            "processed": True,
            "attempts": claimed.attempts,
        }
    )


def _billing_settings_url(request, **query):
    url = reverse("accounts_app:billing")
    if query:
        url = f"{url}?{urlencode(query)}"
    return request.build_absolute_uri(url)


def _payment_step_url(request, **query):
    """The FUNNEL's return address (PR #934 review, blocker 3).

    The provider used to send the browser back to the generic billing page, so
    the success/cancel notices the payment step renders were unreachable — the
    step never saw its own outcome, and success never moved anyone on to the
    product.
    """
    from apps.infra.accounts_app.funnel import payment_step_url

    url = payment_step_url(**query)
    return request.build_absolute_uri(url)


@login_required
@require_POST
def start_card_setup(request):
    """Send the user to the provider's hosted card form (setup, no charge).

    The card becomes usable only when the signed completion webhook arrives.
    The plan posted here must be on the deployment's allowlist (blocker 5) and
    is bound to the provider session's metadata, so the webhook activates the
    plan the user was actually shown.
    """
    from apps.infra.accounts_app.payment_step import funnel_plan
    from apps.infra.auth_app.onboarding import state_for

    if state_for(request.user) is None:
        # Not a funnel account: this endpoint exists for the signup step, and an
        # established account adds a card from billing settings instead.
        messages.error(request, _("Use billing settings to add or change a card."))
        return redirect("accounts_app:billing")

    row = funnel_plan(request.user, requested_id=request.POST.get("plan") or None)
    if row is None:
        messages.error(
            request,
            _(
                "We could not determine which plan to set up. Nothing has been "
                "charged. Please try again, or contact support."
            ),
        )
        return redirect("accounts_app:payment_step")

    try:
        hosted_url = get_billing_provider().start_card_setup(
            request.user,
            pricing_id=row["id"],
            success_url=_payment_step_url(request, setup="complete"),
            cancel_url=_payment_step_url(request, setup="cancelled"),
        )
    except BillingNotConfigured as exc:
        return _service_unavailable(str(exc))
    except BillingOperationRefused as exc:
        messages.error(request, str(exc))
        return redirect("accounts_app:payment_step")
    return redirect(hosted_url)



@login_required
@require_POST
def start_subscription(request):
    """Continue the trial into the chosen paid plan (``pricing_id`` from pricing.json)."""
    try:
        get_billing_provider().start_subscription(
            request.user, pricing_id=request.POST.get("pricing_id", "")
        )
    except BillingNotConfigured as exc:
        return _service_unavailable(str(exc))
    except BillingOperationRefused as exc:
        messages.error(request, str(exc))
        return redirect("accounts_app:billing")
    messages.success(request, _("Your plan is active. Thank you for subscribing."))
    return redirect("accounts_app:billing")


@login_required
@require_POST
def cancel_subscription(request):
    """Stop renewal at the end of the paid period (no proration, per 特商法)."""
    subscription = get_object_or_404(
        request.user.plan_subscriptions, pk=request.POST.get("subscription_pk")
    )
    try:
        get_billing_provider().cancel_subscription(subscription)
    except BillingNotConfigured as exc:
        return _service_unavailable(str(exc))
    messages.success(
        request, _("Your plan will end at the close of the current billing period.")
    )
    return redirect("accounts_app:billing")


@login_required
@require_POST
def open_billing_portal(request):
    """Open the provider's self-service portal (change card or plan, invoices)."""
    try:
        portal_url = get_billing_provider().customer_portal_url(
            request.user, return_url=_billing_settings_url(request)
        )
    except BillingNotConfigured as exc:
        return _service_unavailable(str(exc))
    except BillingOperationRefused as exc:
        messages.error(request, str(exc))
        return redirect("accounts_app:billing")
    return redirect(portal_url)


# EOF
