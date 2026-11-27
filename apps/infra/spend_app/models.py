"""Spend-control state.

Four tables, each with one job:

* :class:`SpendControl` — the cap the account holder chose (``None`` = the
  plan's default from the price catalog).
* :class:`SpendAlert` — one row per (account, billing month, threshold). It is
  both the in-app notification and the idempotency key that makes "alert at
  80 %" fire once per month, however often the sweep runs. The 100 % row's
  ``created_at`` also starts the running-work grace window.
* :class:`BillingAccountState` — payment standing: good, past due (in grace),
  or restricted. A restricted account is READ-ONLY;
  nothing here ever deletes user data.
* :class:`BillingAccountEvent` — append-only history of every state change and
  the provider event that caused it (design §3.6.6).

Launch records are NOT kept here: every billable workload (interactive
terminal, project service, batch job) is ONE ``console_app.WorkloadSession``
row, written by ``console_app.services.workload_sessions``. That row carries
the allocation and the stop reason, is the join the future usage ledger
resolves against (design §3.2) and, until then, the PROVISIONAL compute
source (:mod:`.services.usage`).
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models


class SpendControl(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="spend_control"
    )
    #: The holder's chosen cap in USD per billing month, usage beyond the plan
    #: fee. ``None`` means "use the plan default" so a catalog change reaches
    #: every account that never chose its own value.
    monthly_cap_usd = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Spend control"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monthly_cap_usd__isnull=True)
                | models.Q(monthly_cap_usd__gte=Decimal("0")),
                name="spend_control_cap_non_negative",
            )
        ]

    def __str__(self):
        cap = (
            "plan default"
            if self.monthly_cap_usd is None
            else f"${self.monthly_cap_usd}"
        )
        return f"{self.user.username}: {cap}"


class SpendAlert(models.Model):
    THRESHOLDS = (50, 80, 100)

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="spend_alerts"
    )
    #: Billing month, ``YYYY-MM`` (UTC).
    period = models.CharField(max_length=7)
    threshold = models.PositiveSmallIntegerField()
    spend_usd = models.DecimalField(max_digits=12, decimal_places=4)
    cap_usd = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    emailed_at = models.DateTimeField(null=True, blank=True)
    email_error = models.TextField(blank=True, default="")
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "period", "threshold"],
                name="spend_alert_once_per_period",
            )
        ]

    def __str__(self):
        return f"{self.user.username} {self.period} {self.threshold}%"


class BillingAccountState(models.Model):
    class State(models.TextChoices):
        GOOD = "good", "In good standing"
        PAST_DUE = "past_due", "Payment failed; in grace period"
        RESTRICTED = "restricted", "Restricted: read-only, no new compute"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="billing_account_state"
    )
    state = models.CharField(max_length=16, choices=State.choices, default=State.GOOD)
    past_due_since = models.DateTimeField(null=True, blank=True)
    grace_until = models.DateTimeField(null=True, blank=True)
    reminders_sent = models.PositiveSmallIntegerField(default=0)
    last_reminder_at = models.DateTimeField(null=True, blank=True)
    restricted_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    #: The provider invoice that settled actual usage at cancellation.
    final_invoice_id = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Billing account state"

    def __str__(self):
        return f"{self.user.username}: {self.state}"


class BillingAccountEvent(models.Model):
    """Append-only. Never updated or deleted by application code."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="billing_account_events"
    )
    kind = models.CharField(max_length=64)
    from_state = models.CharField(max_length=16, blank=True, default="")
    to_state = models.CharField(max_length=16, blank=True, default="")
    provider_event_id = models.CharField(max_length=255, blank=True, default="")
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("BillingAccountEvent is append-only")
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} {self.kind} {self.from_state}->{self.to_state}"
