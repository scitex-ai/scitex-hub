"""Billing models: webhook event log, saved cards, and plan subscriptions."""

from django.contrib.auth.models import User
from django.db import models


class BillingEvent(models.Model):
    """Minimal record of signature-verified Stripe webhook events.

    Scaffold only — entitlement logic (mapping events to subscriptions)
    is a separate card (hub-billing-entitlement-minimal). ``event_id``
    is the Stripe event id (``evt_...``) and is unique so webhook
    retries stay idempotent.
    """

    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=255)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]
        verbose_name = "Billing Event"
        verbose_name_plural = "Billing Events"

    def __str__(self):
        return f"{self.event_type} ({self.event_id})"


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
