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
from django.utils import timezone

from ..pricing import format_amount, load_pricing


class BillingNotConfigured(Exception):
    """The provider lacks the keys this operation needs; ``str()`` names them."""


class BillingOperationRefused(Exception):
    """The request is valid but not allowed now (for example, the trial has ended)."""


class BillingModeMismatch(Exception):
    """Test and live configuration disagree — refuse rather than charge someone.

    PR #934 review, blocker 5. A deployment can end up with a live secret key and
    a test price id (or the reverse) by editing one environment variable and not
    the other. Nothing failed loudly before: the session was created, the
    webhook was accepted, and the mistake surfaced as either a real charge in a
    test workflow or a silent no-op in production. Both directions are now
    refused at the boundary that would otherwise do the damage.
    """


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

    def start_card_setup(
        self, user, *, pricing_id: str, success_url: str, cancel_url: str
    ) -> str:
        """Return the hosted page URL where the user enters a card.

        ``pricing_id`` is REQUIRED and is the allowlisted plan the funnel is
        signing this account up for (PR #934 review, blocker 5): it is bound to
        the provider customer/session metadata so the webhook activates the plan
        the user was actually shown, instead of re-deciding it later.
        """

    def verify_webhook(self, payload: bytes, headers) -> dict | None:
        """Return the parsed event when the signature is genuine, else ``None``."""

    def handle_event(self, event: dict) -> None:
        """Apply a verified event to local state (cards, subscriptions)."""

    def subscribable_plans(self) -> list[SubscribablePlan]: ...

    def start_subscription(self, user, *, pricing_id: str):
        """Create the paid plan and return the local ``PlanSubscription``."""

    def create_setup_intent(self, user, *, pricing_id: str):
        """A SetupIntent for the inline Elements form: ``(id, client_secret)``."""

    def confirm_card_setup(self, user, *, setup_intent_id: str):
        """Verify a confirmed SetupIntent, persist the card, start the trial."""

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


def configured_price_ids(price_ids=None) -> dict:
    """``{pricing_id: provider_price_id}`` for this deployment."""
    if price_ids is None:
        price_ids = getattr(settings, "STRIPE_PRICE_IDS", {}) or {}
    return {key: value for key, value in dict(price_ids).items() if value}


def signup_plan_allowlist(price_ids=None) -> list[dict]:
    """The ONLY plans a signup may be placed on: rows this deployment can charge.

    PR #934 review, blocker 5. The step used to accept an arbitrary ``?plan=``
    value and resolve it against the catalog, so a row with no configured
    provider price — or no row at all — could be quoted as the plan someone was
    signing up for, and the selection was then dropped: the POST, the session,
    the customer and the webhook each re-decided from nothing.

    The allowlist is the intersection of the catalog and the configured prices,
    in catalog order. Everything downstream (the step, the POST, the provider
    session's metadata, the webhook) resolves through THIS function, so an id
    that is not in it cannot travel through the funnel at all.
    """
    configured = configured_price_ids(price_ids)
    return [row for row in subscription_pricing_rows() if row.get("id") in configured]


def resolve_signup_plan(pricing_id, price_ids=None) -> dict | None:
    """The allowlisted row for ``pricing_id``, or ``None``.

    ``None`` is a refusal, never a silent fallback to some other plan: a request
    naming a plan this deployment cannot charge for must fail, not be "helpfully"
    upgraded to a different price.
    """
    if not pricing_id:
        return None
    return next(
        (row for row in signup_plan_allowlist(price_ids) if row.get("id") == pricing_id),
        None,
    )


#: Which Stripe mode a key belongs to. Only the mode is derived — the key value
#: itself is never logged, stored, returned or compared anywhere else.
_TEST_KEY_PREFIXES = ("sk_test_", "rk_test_")
_LIVE_KEY_PREFIXES = ("sk_live_", "rk_live_")


def key_environment(secret_key: str | None) -> str:
    """``"test"``, ``"live"`` or ``"unknown"`` for a Stripe secret key."""
    key = (secret_key or "").strip()
    if any(key.startswith(prefix) for prefix in _TEST_KEY_PREFIXES):
        return "test"
    if any(key.startswith(prefix) for prefix in _LIVE_KEY_PREFIXES):
        return "live"
    return "unknown"


def event_matches_key_environment(event, secret_key) -> bool:
    """Whether a webhook event's ``livemode`` agrees with the configured key.

    Cheap, offline, and the check that stops a test-mode signing secret from
    being pointed at a live endpoint (or vice versa): a live event arriving on a
    test key is either a misconfiguration or a replayed payload, and either way
    it must not be applied to local entitlement.
    """
    environment = key_environment(secret_key)
    if environment == "unknown":
        return False
    livemode = bool(_event_field(event, "livemode"))
    return livemode == (environment == "live")


def _event_field(event, name, default=None):
    if isinstance(event, dict):
        return event.get(name, default)
    return getattr(event, name, default)


def price_environment_problems(provider) -> list[str]:
    """Every configured price id that disagrees with the configured key.

    Asks the provider for each price's ``livemode`` (one retrieve per price, so
    call it from an operator check rather than a request path) and reports the
    mismatches instead of raising, so an operator sees ALL of them at once.
    """
    environment = key_environment(getattr(provider, "secret_key", ""))
    if environment == "unknown":
        return ["the configured Stripe secret key is not a recognisable test/live key"]
    problems = []
    for pricing_id, price_id in sorted(configured_price_ids(getattr(provider, "price_ids", None)).items()):
        try:
            price = provider._client().Price.retrieve(price_id)
        except Exception as exc:  # pragma: no cover - network/credential failure
            problems.append(f"{pricing_id} ({price_id}): could not be read back ({exc})")
            continue
        if bool(_event_field(price, "livemode")) != (environment == "live"):
            problems.append(
                f"{pricing_id} ({price_id}) is a {('live' if _event_field(price, 'livemode') else 'test')} "
                f"price but the secret key is {environment}"
            )
    return problems


def pricing_row_price_text(row: dict) -> str:
    return format_amount(row["amount"], row.get("unit", "once"), row.get("from_price", False))


def trial_days() -> int:
    rows = subscription_pricing_rows()
    return max(row.get("attributes", {}).get("free_trial", {}).get("days", 0) for row in rows)


def confirmed_trial_window(user):
    """The PROVIDER-confirmed trial window, or ``None`` if there is not one yet.

    PR #934 review, blocker 2. This is the only source a date may be quoted
    from. ``status="trialing"`` plus a provider ``trial_end`` is a fact Stripe
    reported; anything else (including "a card is saved") is not.

    Deliberately not inferred from the local model's arithmetic: the fields on
    ``PlanSubscription`` are written from provider responses only
    (``stripe_provider._sync_subscription``), so a row that exists here was
    confirmed by the provider.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    from ..models import PlanSubscription

    subscription = (
        PlanSubscription.objects.filter(user=user, status="trialing")
        .exclude(trial_end=None)
        .order_by("-created_at")
        .first()
    )
    if subscription is None:
        return None
    start = subscription.trial_start or subscription.created_at
    return start, subscription.trial_end


def trial_window(user) -> tuple[datetime, datetime]:
    """The trial the funnel is offering: provider-confirmed, else from today.

    WHAT THIS USED TO BE, AND WHY IT WAS A DEFECT (blocker 2). The window ran
    from ``user.date_joined`` — the moment the signup FORM was submitted, before
    the OTP was entered and before any card existed. So the payment step quoted
    a trial end and a first-charge date for a trial that had not started, and
    could already be partly spent by the time the user reached the step; and if
    the user never paid, the disclosure had still promised a date. Nothing was
    backed by provider state.

    Now: once a provider-confirmed subscription exists, its own window is
    quoted. Until then, the honest answer is "the trial starts when your card is
    validated and runs for N days", which is what the step says — so the first
    charge date IS the trial end, as the disclosure promises.
    """
    confirmed = confirmed_trial_window(user)
    if confirmed is not None:
        return confirmed
    start = timezone.now()
    return start, start + timedelta(days=trial_days())


def card_registration_is_open() -> bool:
    try:
        return get_billing_provider().card_registration_open
    except BillingNotConfigured:
        return False


def inline_card_form_info() -> dict:
    """Publishable key + availability for the inline Elements form.

    Returns ``{"open": bool, "publishable_key": str}``. The key is public by
    design; an empty key means the funnel offers the hosted Checkout button
    only.
    """
    try:
        provider = get_billing_provider()
    except BillingNotConfigured:
        return {"open": False, "publishable_key": ""}
    return {
        "open": bool(getattr(provider, "inline_card_form_open", False)),
        "publishable_key": getattr(provider, "publishable_key", "") or "",
    }


def post_signup_redirect_url(user) -> str:
    """Card-required signup: a verified user goes to the payment step, always.

    Card: hub-signup-email-stripe-funnel-20260917. This used to return the user's
    own workspace when the provider was not configured — which FAILED OPEN: a
    verified signup walked straight past the card requirement into the product, and
    the funnel silently had two policies depending on an environment variable. The
    payment step is the honest destination in every case; what changes with the
    provider is only what that step can offer (its `not_open` state says activation
    is waiting), never whether the user is routed there.

    PR #934 review, blocker 7: the answer now comes from the durable onboarding
    authority rather than from this function's own opinion, so the OTP handler
    and the allauth social adapter (``SciTexSocialAccountAdapter``, which used to
    return ``LOGIN_REDIRECT_URL`` and skip the funnel entirely) cannot diverge.
    Kept as a function because it is the name the auth surfaces already import.
    """
    from apps.infra.auth_app.onboarding import next_url

    return next_url(user)
