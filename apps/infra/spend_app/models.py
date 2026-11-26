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
* :class:`WorkloadSession` — one row per billable workload launch (interactive
  terminal, notebook/service, batch job). It is the join the future usage
  ledger resolves against (design §3.2) and, until then, the PROVISIONAL
  compute source.
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


class WorkloadSession(models.Model):
    class Kind(models.TextChoices):
        TERMINAL = "terminal", "Interactive terminal"
        SERVICE = "service", "Project service (notebook, TensorBoard, ...)"
        JOB = "job", "Batch job"

    class StopReason(models.TextChoices):
        NONE = "", "Running"
        COMPLETED = "completed", "Finished on its own"
        USER = "user", "Stopped by the user"
        IDLE = "idle", "Idle auto-stop"
        SPEND_CAP = "spend_cap", "Monthly spend cap reached"
        RESTRICTED = "restricted", "Account restricted"
        EXPIRED = "expired", "Time limit reached"
        LOST = "lost", "Ended without a stop record"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="workload_sessions"
    )
    project_id = models.BigIntegerField(null=True, blank=True)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    #: Allocated (reserved) resources — compute is billed by allocation.
    cpus = models.PositiveSmallIntegerField(default=1)
    memory_gb = models.PositiveSmallIntegerField(default=4)
    gpus = models.PositiveSmallIntegerField(default=0)
    #: Upper bound on wall time when no stop is ever recorded (a SLURM job's
    #: time limit). ``None`` = open until stopped.
    max_seconds = models.PositiveIntegerField(null=True, blank=True)
    scheduler_id = models.CharField(max_length=128, blank=True, default="")
    label = models.CharField(max_length=128, blank=True, default="")
    started_at = models.DateTimeField()
    stopped_at = models.DateTimeField(null=True, blank=True)
    stop_reason = models.CharField(
        max_length=16, choices=StopReason.choices, blank=True, default=""
    )

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "stopped_at"]),
            models.Index(fields=["user", "started_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} {self.kind} {self.started_at:%Y-%m-%d %H:%M}"
