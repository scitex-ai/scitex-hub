"""30-day cancellation, billed on actual usage (pricing decision #3).

Within ``cancellation_window_days`` of the subscription's start the holder may
cancel at any time and is billed only for what was actually used up to that
moment:

1. the month-to-date usage (via the one :class:`UsageSource`) is added to the
   customer as a pending invoice item, with an idempotency key derived from the
   subscription, so a double click cannot add it twice;
2. the subscription is cancelled IMMEDIATELY with ``invoice_now=True`` and
   ``prorate=True``: Stripe issues the final invoice now, sweeping in that item
   and prorating any plan fee to the time actually used (a trialing
   subscription has no fee to prorate);
3. the account falls back to the Free plan. Nothing is deleted.

TEST MODE ONLY. The provider call refuses unless the configured secret key is
a Stripe test key (``sk_test_``/``rk_test_``): spend controls never create live
objects. Taking this live is a deliberate later change, not a setting.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import usage

logger = logging.getLogger("scitex")


class CancellationRefused(Exception):
    pass


@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    reason: str
    subscription: object | None = None
    window_ends: object | None = None


def eligibility(user, *, now=None) -> Eligibility:
    from apps.infra.public_app.models import PlanSubscription

    now = now or timezone.now()
    sub = (
        PlanSubscription.objects.filter(
            user=user, status__in=PlanSubscription.CURRENT_STATUSES
        )
        .order_by("-created_at")
        .first()
    )
    if sub is None:
        return Eligibility(False, "no_subscription")
    start = sub.trial_start or sub.created_at
    ends = start + timedelta(days=settings.SPEND_CONTROLS["cancellation_window_days"])
    if now >= ends:
        return Eligibility(False, "window_closed", sub, ends)
    return Eligibility(True, "ok", sub, ends)


def usage_amount_cents(snapshot: usage.UsageSnapshot) -> int:
    """USD cents for the usage invoice item (USD is the catalog currency)."""
    return int(
        (snapshot.total_usd * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def _require_test_mode(provider) -> None:
    from apps.infra.public_app.services.billing_provider import key_environment

    if key_environment(getattr(provider, "secret_key", "")) != "test":
        raise CancellationRefused(
            "Self-service cancellation with usage billing runs in Stripe TEST mode "
            "only for now; contact support to cancel."
        )


def cancel_with_actual_usage(user, *, provider=None, now=None) -> dict:
    """Cancel now, invoice actual usage. Returns what was sent to the provider."""
    from apps.infra.public_app.services.billing_provider import get_billing_provider

    from ..models import BillingAccountEvent, BillingAccountState

    now = now or timezone.now()
    elig = eligibility(user, now=now)
    if not elig.eligible:
        raise CancellationRefused(
            "The 30-day cancellation window has closed; your plan can still be "
            "cancelled at the end of the billing period."
            if elig.reason == "window_closed"
            else "There is no active plan to cancel."
        )
    sub = elig.subscription
    provider = provider or get_billing_provider()
    _require_test_mode(provider)
    client = provider._client()

    snap = usage.current_snapshot(user, fresh=True)
    cents = usage_amount_cents(snap)
    key = f"scitex-cancel30-{sub.provider_subscription_id}"
    item_id = ""
    if cents > 0:
        item = client.InvoiceItem.create(
            customer=sub.provider_customer_id,
            amount=cents,
            currency="usd",
            description=(
                f"SciTeX Cloud usage {snap.window_start:%Y-%m-%d} to "
                f"{snap.window_end:%Y-%m-%d} (cancelled within 30 days)"
            ),
            metadata={
                "user_pk": str(user.pk),
                "period": snap.period,
                "usage_source": "provisional" if snap.provisional else "ledger",
            },
            idempotency_key=f"{key}-usage",
        )
        item_id = getattr(item, "id", None) or (
            item.get("id") if isinstance(item, dict) else ""
        )
    cancelled = client.Subscription.cancel(
        sub.provider_subscription_id,
        invoice_now=True,
        prorate=True,
        idempotency_key=f"{key}-cancel",
    )
    invoice_id = (
        getattr(cancelled, "latest_invoice", None)
        or (cancelled.get("latest_invoice") if isinstance(cancelled, dict) else "")
        or ""
    )
    with transaction.atomic():
        sub.status = "canceled"
        sub.cancel_at_period_end = False
        sub.save(update_fields=["status", "cancel_at_period_end", "updated_at"])
        row, _ = BillingAccountState.objects.select_for_update().get_or_create(
            user=user
        )
        row.cancelled_at = now
        row.final_invoice_id = str(invoice_id)[:255]
        row.save(update_fields=["cancelled_at", "final_invoice_id", "updated_at"])
        BillingAccountEvent.objects.create(
            user=user,
            kind="cancelled_within_window",
            from_state=row.state,
            to_state=row.state,
            detail={
                "subscription": sub.provider_subscription_id,
                "usage_usd": str(snap.total_usd),
                "usage_cents": cents,
                "usage_provisional": snap.provisional,
                "invoice_item": item_id,
                "final_invoice": str(invoice_id),
            },
        )
    usage.invalidate(user)
    logger.info("user %s cancelled within window; usage %s cents", user.pk, cents)
    return {
        "usage_cents": cents,
        "invoice_item": item_id,
        "final_invoice": str(invoice_id),
    }


__all__ = [
    "CancellationRefused",
    "Eligibility",
    "cancel_with_actual_usage",
    "eligibility",
    "usage_amount_cents",
]
