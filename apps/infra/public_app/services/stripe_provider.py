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
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.utils import timezone

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

    def __init__(self, *, secret_key="", webhook_secret="", price_ids=None, stripe_client=None):
        self.secret_key = secret_key or ""
        self.webhook_secret = webhook_secret or ""
        self.price_ids = dict(price_ids or {})
        self._stripe_client = stripe_client

    @classmethod
    def from_settings(cls, **overrides):
        values = {
            "secret_key": settings.STRIPE_SECRET_KEY,
            "webhook_secret": settings.STRIPE_WEBHOOK_SECRET,
            "price_ids": getattr(settings, "STRIPE_PRICE_IDS", {}),
        }
        values.update(overrides)
        return cls(**values)

    @property
    def card_registration_open(self) -> bool:
        return bool(self.secret_key)

    def _client(self):
        if not self.secret_key:
            raise BillingNotConfigured(
                "SCITEX_HUB_STRIPE_SECRET_KEY is not configured. Card setup and "
                "subscriptions are disabled until Stripe keys are set in the "
                "environment (SECRET/.env.*)."
            )
        return self._stripe_client or stripe_setup.build_stripe_client(self.secret_key)

    def start_card_setup(self, user, *, success_url, cancel_url):
        session = stripe_setup.start_card_setup(
            user, stripe_client=self._client(), success_url=success_url, cancel_url=cancel_url
        )
        return session.url

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
            if row is not None:
                logger.info("Card setup completed for user %s", row.user_id)
        elif event_type in SUBSCRIPTION_EVENT_TYPES:
            self._sync_subscription(_field(_field(event, "data"), "object"))

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

        trial_start, trial_end = trial_window(user)
        create_kwargs = {
            "customer": card.stripe_customer_id,
            "items": [{"price": plan.provider_price_id}],
            "default_payment_method": card.stripe_payment_method_id,
            "metadata": {"user_pk": str(user.pk), "pricing_id": pricing_id},
        }
        # 特商法: continuing during the trial bills the first period from registration.
        if timezone.now() < trial_end:
            create_kwargs["backdate_start_date"] = int(trial_start.timestamp())
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
            },
        )
        return row
