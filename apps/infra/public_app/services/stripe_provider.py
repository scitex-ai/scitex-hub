"""Stripe implementation of ``BillingProvider``.

Card entry happens only on Stripe-hosted pages (Checkout in setup mode and the
Customer Portal), so SciTeX never handles PAN/CVC. The Stripe client is an
injected collaborator (``stripe_client=``) so tests pass a hand-rolled fake.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime
from datetime import timezone as dt_timezone

from django.conf import settings

from . import stripe_setup
from .billing_provider import (
    BillingNotConfigured,
    BillingOperationRefused,
    SubscribablePlan,
    pricing_row_price_text,
    subscription_pricing_rows,
    trial_window,
)
from .stripe_setup import _field

logger = logging.getLogger("scitex")

# Mirrors stripe-python's DEFAULT_TOLERANCE; blocks replay of captured payloads.
STRIPE_SIGNATURE_TOLERANCE_SECONDS = 300

SUBSCRIPTION_EVENT_TYPES = (
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
)


def verify_stripe_signature(
    payload: bytes,
    signature_header: str,
    secret: str,
    tolerance_seconds: int = STRIPE_SIGNATURE_TOLERANCE_SECONDS,
) -> bool:
    """Check a ``Stripe-Signature: t=<ts>,v1=<hex>`` header (HMAC-SHA256 of ``t.payload``)."""
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
    return any(hmac.compare_digest(expected, candidate) for candidate in candidate_signatures)


def _as_datetime(unix_seconds):
    if not unix_seconds:
        return None
    return datetime.fromtimestamp(int(unix_seconds), tz=dt_timezone.utc)


def _current_period_end(stripe_subscription):
    # API versions from 2025-03-31 moved the period onto each subscription item.
    top_level = _field(stripe_subscription, "current_period_end")
    if top_level:
        return top_level
    items = _field(_field(stripe_subscription, "items"), "data") or []
    return _field(items[0], "current_period_end") if items else None


class StripeBillingProvider:
    name = "stripe"

    def __init__(self, *, secret_key="", webhook_secret="", price_ids=None, stripe_client=None, publishable_key=""):
        self.secret_key = secret_key or ""
        self.webhook_secret = webhook_secret or ""
        self.price_ids = dict(price_ids or {})
        self._stripe_client = stripe_client
        self.publishable_key = publishable_key or ""

    @classmethod
    def from_settings(cls, **overrides):
        values = {
            "secret_key": settings.STRIPE_SECRET_KEY,
            "webhook_secret": settings.STRIPE_WEBHOOK_SECRET,
            "price_ids": getattr(settings, "STRIPE_PRICE_IDS", {}),
            "publishable_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
        }
        values.update(overrides)
        return cls(**values)

    @property
    def card_registration_open(self) -> bool:
        return bool(self.secret_key)

    @property
    def inline_card_form_open(self) -> bool:
        """Whether the inline Elements form can be offered.

        Needs the secret key (SetupIntent creation) AND the publishable key
        (Stripe.js). Without the publishable key the funnel keeps the hosted
        Checkout button only.
        """
        return bool(self.secret_key and self.publishable_key)

    def _client(self):
        if not self.secret_key:
            raise BillingNotConfigured(
                "SCITEX_HUB_STRIPE_SECRET_KEY is not configured. Card setup and "
                "subscriptions are disabled until Stripe keys are set in the "
                "environment (SECRET/.env.*)."
            )
        return self._stripe_client or stripe_setup.build_stripe_client(self.secret_key)

    def start_card_setup(self, user, *, pricing_id, success_url, cancel_url):
        setup = stripe_setup.start_card_setup(
            user,
            pricing_id=pricing_id,
            stripe_client=self._client(),
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return setup.url

    def create_setup_intent(self, user, *, pricing_id: str):
        """A SetupIntent for the inline Elements form.

        Returns ``(setup_intent_id, client_secret)``. The browser confirms it
        with Stripe.js; :meth:`confirm_card_setup` verifies the result.
        """
        return stripe_setup.create_card_setup_intent(
            user, pricing_id=pricing_id, stripe_client=self._client()
        )

    def confirm_card_setup(self, user, *, setup_intent_id: str):
        """Verify an inline SetupIntent, persist the card and start the trial.

        Returns the ``PaymentMethod`` row, or ``None`` when the intent cannot
        be attributed to this user.
        """
        from apps.infra.auth_app.onboarding import state_for

        card = stripe_setup.confirm_card_setup(
            user, setup_intent_id=setup_intent_id, stripe_client=self._client()
        )
        if card is None:
            return None
        authority = state_for(user)
        pricing_id = (authority.pricing_id if authority else "") or ""
        if pricing_id:
            self.activate_trial(
                user,
                pricing_id=pricing_id,
                customer_id=card.stripe_customer_id,
                payment_method_id=card.stripe_payment_method_id,
                seed=setup_intent_id,
                stripe_client=self._client(),
            )
        return card

    def verify_webhook(self, payload, headers):
        if not self.webhook_secret:
            raise BillingNotConfigured(
                "SCITEX_HUB_STRIPE_WEBHOOK_SECRET is not configured. The webhook "
                "is disabled until the signing secret is set in the environment "
                "(SECRET/.env.*)."
            )
        signature_header = headers.get("Stripe-Signature", "")
        if not verify_stripe_signature(payload, signature_header, self.webhook_secret):
            return None
        return json.loads(payload.decode("utf-8"))

    def handle_event(self, event):
        event_type = event.get("type", "")
        if event_type == "checkout.session.completed":
            client = self._client() if self.secret_key else None
            row = stripe_setup.apply_setup_completed(event, stripe_client=client)
            if row is None:
                return
            logger.info("Card setup completed for user %s", row.user_id)
            # A validated card is NOT an activated trial: the user has $0 due
            # today and a provider-confirmed subscription has to exist before
            # any date is quoted or any product is opened (blockers 2 and 3).
            self.activate_trial_from_setup(event, row, stripe_client=client)
        elif event_type in SUBSCRIPTION_EVENT_TYPES:
            self._confirm_activation(
                self._sync_subscription(_field(_field(event, "data"), "object"))
            )

    def activate_trial_from_setup(self, event, card, *, stripe_client=None):
        """Create the trial the payment step promised, from the completed setup.

        Reads the plan from the SESSION's metadata (written server-side when the
        session was created), never from a browser parameter, and is idempotent:
        a replayed ``checkout.session.completed`` finds the subscription it
        already created and returns it.
        """
        from django.contrib.auth import get_user_model

        session = _field(_field(event, "data"), "object")
        pricing_id = stripe_setup.session_pricing_id(event)
        user_pk = _field(session, "client_reference_id")
        user = card.user if card is not None else None
        if user is None and user_pk:
            user = get_user_model().objects.filter(pk=int(user_pk)).first()
        if user is None:
            logger.warning("setup completed with no mappable user; no trial activated")
            return None
        return self.activate_trial(
            user,
            pricing_id=pricing_id,
            customer_id=_field(session, "customer") or card.stripe_customer_id,
            payment_method_id=card.stripe_payment_method_id,
            seed=_field(session, "id") or "",
            stripe_client=stripe_client,
        )

    def activate_trial(
        self, user, *, pricing_id, customer_id, payment_method_id, seed="", stripe_client=None
    ):
        """Start a PROVIDER-CONFIRMED trial for ``user``. Idempotent.

        Blocker 2 was that the funnel only ever opened a zero-dollar card setup:
        no subscription, no entitlement, no trial — while the step promised a
        trial end and a first charge. This creates the real trialing
        subscription at the provider, with ``trial_end`` computed from the same
        ``trial_days()`` the disclosure quotes, and persists the provider's own
        answer (status + trial boundaries) rather than our arithmetic.

        IDEMPOTENCY, in two layers: a live subscription for this user short-
        circuits before any provider call, and the create carries a deterministic
        idempotency key. A replayed webhook therefore cannot start two trials.
        """
        from ..models import PlanSubscription

        plan = next(
            (p for p in self.subscribable_plans() if p.pricing_id == pricing_id), None
        )
        if plan is None:
            # An unnameable plan cannot be charged. Refuse loudly and leave the
            # account at PAYMENT; the card is kept, so a corrected catalog is
            # the only thing needed to finish activation.
            logger.error(
                "Refusing to activate a trial for user %s: pricing_id %r is not on "
                "this deployment's allowlist", user.pk, pricing_id,
            )
            return None

        existing = (
            PlanSubscription.objects.filter(user=user, status__in=("trialing", "active", "past_due"))
            .order_by("-created_at")
            .first()
        )
        if existing is not None:
            logger.info("Trial for user %s already exists (%s); not starting another", user.pk, existing.provider_subscription_id)
            return existing

        client = stripe_client or self._client()
        _, trial_end = trial_window(user)
        stripe_subscription = client.Subscription.create(
            customer=customer_id,
            items=[{"price": plan.provider_price_id}],
            default_payment_method=payment_method_id,
            trial_end=int(trial_end.timestamp()),
            metadata={"user_pk": str(user.pk), "pricing_id": pricing_id},
            idempotency_key=f"scitex-trial-{user.pk}-{pricing_id}-{seed or 'direct'}",
        )
        row = self._sync_subscription(stripe_subscription, user=user)
        self._confirm_activation(row)
        return row

    def _confirm_activation(self, row):
        """Advance the onboarding authority once the provider has confirmed.

        THE boundary of the funnel: everything before this is a request, and
        this is the first moment a provider-issued subscription exists. Called
        from webhook handling only.
        """
        if row is None or row.status not in ("trialing", "active", "past_due"):
            return row
        from apps.infra.auth_app.onboarding import mark_activated

        mark_activated(row.user, pricing_id=row.pricing_id)
        return row


    def subscribable_plans(self):
        return [
            SubscribablePlan(
                pricing_id=row["id"],
                label=row["label"],
                price_text=pricing_row_price_text(row),
                provider_price_id=self.price_ids[row["id"]],
            )
            for row in subscription_pricing_rows()
            if self.price_ids.get(row["id"])
        ]

    def start_subscription(self, user, *, pricing_id):
        plan = next((p for p in self.subscribable_plans() if p.pricing_id == pricing_id), None)
        if plan is None:
            raise BillingOperationRefused(f"The plan {pricing_id!r} is not offered online.")
        card = user.payment_methods.filter(is_usable=True, is_default=True).first()
        if card is None:
            raise BillingOperationRefused("Add a card before choosing a plan.")
        if any(s.is_current for s in user.plan_subscriptions.all()):
            raise BillingOperationRefused("You already have an active plan.")

        create_kwargs = {
            "customer": card.stripe_customer_id,
            "items": [{"price": plan.provider_price_id}],
            "default_payment_method": card.stripe_payment_method_id,
            "metadata": {"user_pk": str(user.pk), "pricing_id": pricing_id},
        }
        # NO BACKDATING (PR #934 review, blocker 2). This used to backdate the
        # first period to ``date_joined`` "because the customer was in their
        # trial" — but that date is the signup FORM's, the trial it referred to
        # did not exist at the provider, and reaching this branch requires having
        # no current subscription at all (the guard above refuses when there is
        # one). The 特商法 rule that a converted trial bills from the trial's
        # start is now satisfied where the trial actually starts: the funnel
        # creates the trialing subscription with the provider's own ``trial_end``
        # (``activate_trial``), so Stripe bills the period from that start.
        stripe_subscription = self._client().Subscription.create(**create_kwargs)
        return self._sync_subscription(stripe_subscription, user=user)

    def cancel_subscription(self, subscription):
        stripe_subscription = self._client().Subscription.modify(
            subscription.provider_subscription_id, cancel_at_period_end=True
        )
        return self._sync_subscription(stripe_subscription, user=subscription.user)

    def customer_portal_url(self, user, *, return_url):
        customer_id = stripe_setup._existing_customer_id(user)
        if not customer_id:
            raise BillingOperationRefused("Add a card before opening the billing portal.")
        session = self._client().billing_portal.Session.create(
            customer=customer_id, return_url=return_url
        )
        return session.url

    def _sync_subscription(self, stripe_subscription, *, user=None):
        from django.contrib.auth import get_user_model

        from ..models import PlanSubscription

        subscription_id = _field(stripe_subscription, "id")
        if not subscription_id:
            return None
        existing = PlanSubscription.objects.filter(provider_subscription_id=subscription_id).first()
        metadata = _field(stripe_subscription, "metadata") or {}
        if user is None and existing is not None:
            user = existing.user
        if user is None and _field(metadata, "user_pk"):
            user = get_user_model().objects.filter(pk=int(_field(metadata, "user_pk"))).first()
        if user is None:
            logger.warning("Subscription %s has no mappable user", subscription_id)
            return None

        row, _ = PlanSubscription.objects.update_or_create(
            provider_subscription_id=subscription_id,
            defaults={
                "user": user,
                "provider": self.name,
                "provider_customer_id": _field(stripe_subscription, "customer") or "",
                "pricing_id": _field(metadata, "pricing_id") or (existing.pricing_id if existing else ""),
                "status": _field(stripe_subscription, "status") or "incomplete",
                "cancel_at_period_end": bool(_field(stripe_subscription, "cancel_at_period_end")),
                "current_period_end": _as_datetime(_current_period_end(stripe_subscription)),
                # The PROVIDER's trial boundaries, stored verbatim. These are
                # what the funnel is allowed to quote (blocker 2); nothing here
                # is derived from date_joined or from our own arithmetic.
                "trial_start": _as_datetime(_field(stripe_subscription, "trial_start")),
                "trial_end": _as_datetime(_field(stripe_subscription, "trial_end")),
            },
        )
        return row
