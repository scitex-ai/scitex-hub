"""Provider-neutral billing interface used by the billing views.

Views only talk to a ``BillingProvider``. Stripe is the one implementation
today (services/stripe_provider.py); a Japanese processor such as PAY.JP or
KOMOJU would be a second class registered in ``PROVIDER_FACTORIES``, with no
view change.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from django.conf import settings
from django.urls import reverse

from ..pricing import format_amount, load_pricing


class BillingNotConfigured(Exception):
    """The provider lacks the keys this operation needs; ``str()`` names them."""


class BillingOperationRefused(Exception):
    """The request is valid but not allowed now (for example, the trial has ended)."""


@dataclass(frozen=True)
class SubscribablePlan:
    pricing_id: str
    label: str
    price_text: str
    provider_price_id: str


class BillingProvider(Protocol):
    name: str

    @property
    def card_registration_open(self) -> bool: ...

    def start_card_setup(self, user, *, success_url: str, cancel_url: str) -> str:
        """Return the hosted page URL where the user enters a card."""

    def verify_webhook(self, payload: bytes, headers) -> dict | None:
        """Return the parsed event when the signature is genuine, else ``None``."""

    def handle_event(self, event: dict) -> None:
        """Apply a verified event to local state (cards, subscriptions)."""

    def subscribable_plans(self) -> list[SubscribablePlan]: ...

    def start_subscription(self, user, *, pricing_id: str):
        """Create the paid plan and return the local ``PlanSubscription``."""

    def cancel_subscription(self, subscription):
        """Stop renewal at period end and return the updated ``PlanSubscription``."""

    def customer_portal_url(self, user, *, return_url: str) -> str:
        """Return the provider's self-service page (card, plan, invoices)."""


def _stripe_factory(**overrides):
    from .stripe_provider import StripeBillingProvider

    return StripeBillingProvider.from_settings(**overrides)


PROVIDER_FACTORIES = {"stripe": _stripe_factory}


def get_billing_provider(**overrides) -> BillingProvider:
    """Build the configured provider; ``overrides`` reach its constructor (tests)."""
    name = getattr(settings, "BILLING_PROVIDER", "stripe")
    if name not in PROVIDER_FACTORIES:
        raise BillingNotConfigured(
            f"SCITEX_HUB_BILLING_PROVIDER={name!r} is not one of {sorted(PROVIDER_FACTORIES)}."
        )
    return PROVIDER_FACTORIES[name](**overrides)


def subscription_pricing_rows() -> list[dict]:
    """The pricing.json rows a customer can subscribe to online (fixed monthly price)."""
    return [
        row
        for row in load_pricing()["published_prices"]
        if row.get("category") == "subscription"
        and row.get("amount", 0) > 0
        and not row.get("from_price")
    ]


def pricing_row_price_text(row: dict) -> str:
    return format_amount(row["amount"], row.get("unit", "once"), row.get("from_price", False))


def trial_days() -> int:
    rows = subscription_pricing_rows()
    return max(row.get("attributes", {}).get("free_trial", {}).get("days", 0) for row in rows)


def trial_window(user) -> tuple[datetime, datetime]:
    """Trial runs from registration (``date_joined``), per the 特商法 page."""
    start = user.date_joined
    return start, start + timedelta(days=trial_days())


def card_registration_is_open() -> bool:
    try:
        return get_billing_provider().card_registration_open
    except BillingNotConfigured:
        return False


def post_signup_redirect_url(user) -> str:
    """Card-required signup: a verified user adds a card next, once registration is open.

    Since the funnel card (hub-signup-email-stripe-funnel-20260917) that next step
    is the dedicated payment step rather than the general billing settings page: it
    states the terms before the provider's page and carries the single
    'Continue to secure Stripe' action. Billing settings remains one click away.
    """
    if card_registration_is_open():
        return reverse("accounts_app:payment_step")
    return f"/{user.username}/"
