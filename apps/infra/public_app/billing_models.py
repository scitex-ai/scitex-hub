"""Billing models: webhook event log, saved cards, and plan subscriptions."""

from django.contrib.auth.models import User
from django.db import models


class BillingEvent(models.Model):
    """Minimal record of signature-verified Stripe webhook events.

    ``event_id`` is the Stripe event id (``evt_...``) and is unique, so a
    RETRY of the same event can be recognised. Recognising it is only half the
    job: PR #934 review, blocker 6, was that ``get_or_create`` deduplicated the
    ROW while the handler ran unconditionally afterwards, so a replayed event
    re-ran its side effects. ``status`` is what makes processing idempotent
    instead of merely recording idempotent — see
    ``apps.infra.public_app.services.webhook_processing``, which implements the
    claim/complete/release protocol and is the only thing that may move it.
    """

    class Status(models.TextChoices):
        RECEIVED = "received", "Received, not yet processed"
        PROCESSING = "processing", "Claimed by a worker"
        PROCESSED = "processed", "Applied to local state"
        FAILED = "failed", "Last attempt raised; a retry may claim it"

    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=255)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)
    #: Refreshed on every state change, so it doubles as the CLAIM timestamp the
    #: stale-claim lease is measured against (see ``webhook_processing``).
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED)
    #: How many times a worker has claimed this event. Visible in the admin so a
    #: poison event is obvious rather than merely retried forever.
    attempts = models.PositiveIntegerField(default=0)
    processed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-received_at"]
        verbose_name = "Billing Event"
        verbose_name_plural = "Billing Events"

    def __str__(self):
        return f"{self.event_type} ({self.event_id}) [{self.status}]"

    @property
    def is_processed(self) -> bool:
        return self.status == self.Status.PROCESSED


class BillingSetupSession(models.Model):
    """The ONE hosted card-setup attempt an account has in flight.

    PR #934 review, blocker 4. ``start_card_setup`` created a Stripe customer and
    a Checkout session on every POST, so two clicks before the webhook arrived
    produced two customers, two sessions and two different customer ids — with
    the account's later subscription attributable to whichever one won. Nothing
    was persistent, so nothing could be reused, and no Stripe idempotency key was
    supplied either.

    This row is that persistence: one per account (``OneToOne``), carrying the
    customer id, the CURRENT open session and a monotonic ``attempt`` counter.
    The provider calls in :mod:`apps.infra.public_app.services.stripe_setup` take
    a lock on it and derive their Stripe idempotency keys from it, which is what
    makes the second click return the FIRST session instead of minting a second.
    """

    class Status(models.TextChoices):
        #: A hosted page is open and can still be returned to at no cost.
        OPEN = "open", "Open"
        #: The provider confirmed it (the card is saved and activation ran).
        COMPLETED = "completed", "Completed"
        #: The user came back without finishing; a retry opens a new attempt.
        CANCELLED = "cancelled", "Cancelled"
        #: The provider call failed; the account may retry.
        FAILED = "failed", "Failed"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="billing_setup"
    )
    provider = models.CharField(max_length=32, default="stripe")
    #: The allowlisted pricing.json row this attempt is for. Part of the
    #: idempotency key, so changing plan cannot reuse the old session.
    pricing_id = models.CharField(max_length=64, blank=True, default="")
    #: How many hosted sessions this account has been given. Part of the Stripe
    #: idempotency key, so retries reuse one session and a genuine retry does not
    #: collide with it.
    attempt = models.PositiveIntegerField(default=0)
    stripe_customer_id = models.CharField(max_length=255, blank=True, default="")
    session_id = models.CharField(max_length=255, blank=True, default="")
    session_url = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Billing Setup Session"
        verbose_name_plural = "Billing Setup Sessions"

    def __str__(self):
        return f"{self.user.username} — attempt {self.attempt} ({self.status})"


class PaymentMethod(models.Model):
    """A user's validated card, stored as Stripe identifiers + safe display
    metadata ONLY (never PAN/CVC — the card is captured on Stripe's hosted
    Checkout ``mode="setup"`` page).

    ``is_usable`` is flipped true by the SIGNED ``checkout.session.completed``
    webhook (a zero-dollar setup success is the usability validation), and the
    newest validated card is ``is_default``. See services/stripe_setup.py.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="payment_methods"
    )
    # Stripe identifiers (safe to store; not card data)
    stripe_customer_id = models.CharField(max_length=255, blank=True, default="")
    stripe_payment_method_id = models.CharField(max_length=255, unique=True)
    # Safe display metadata (brand / last4 / expiry — never the number)
    brand = models.CharField(max_length=32, blank=True, default="")
    last4 = models.CharField(max_length=4, blank=True, default="")
    exp_month = models.PositiveSmallIntegerField(null=True, blank=True)
    exp_year = models.PositiveSmallIntegerField(null=True, blank=True)
    # Validation / usage state
    is_usable = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]
        verbose_name = "Payment Method"
        verbose_name_plural = "Payment Methods"

    def __str__(self):
        shown = f"{self.brand} •••• {self.last4}" if self.last4 else self.stripe_payment_method_id
        return f"{self.user.username} — {shown}"


class PlanSubscription(models.Model):
    """A paid SciTeX Cloud plan held with the billing provider.

    ``pricing_id`` is the pricing.json row id. The row mirrors the provider
    (kept in sync by subscription webhooks); it never leads it.
    """

    CURRENT_STATUSES = ("trialing", "active", "past_due", "incomplete")

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="plan_subscriptions"
    )
    provider = models.CharField(max_length=32, default="stripe")
    provider_subscription_id = models.CharField(max_length=255, unique=True)
    provider_customer_id = models.CharField(max_length=255, blank=True, default="")
    pricing_id = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=32, default="incomplete")
    cancel_at_period_end = models.BooleanField(default=False)
    current_period_end = models.DateTimeField(null=True, blank=True)
    #: The PROVIDER's own trial boundaries (Stripe ``trial_start``/``trial_end``).
    #: Written only from provider responses — see
    #: ``billing_provider.confirmed_trial_window``, which is the only thing the
    #: funnel is allowed to quote a date from (PR #934 review, blocker 2).
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Plan Subscription"
        verbose_name_plural = "Plan Subscriptions"

    def __str__(self):
        return f"{self.user.username} — {self.pricing_id} ({self.status})"

    @property
    def is_current(self):
        return self.status in self.CURRENT_STATUSES
