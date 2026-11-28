"""Alerts: in-app rows + email through the Hub's normal mail path.

In-app: a :class:`~apps.infra.spend_app.models.SpendAlert` row, shown by the
site-wide banner (``context_processors.spend_banner``) and on Settings > Spend
controls until read. Email: Django's ``send_mail`` with the Hub's configured
backend and sender, the same path the OTP and password-reset mails use.

A failed send is RECORDED on the alert (``email_error``) and logged at error
level; it never silently passes and never blocks the in-app alert.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from config import branding

from . import gate

logger = logging.getLogger("scitex")


def _site() -> str:
    return getattr(settings, "SITE_URL", "").rstrip("/")


def send_account_email(user, subject: str, body: str) -> str:
    """Send one account email. Returns '' on success, else the error text."""
    if not user.email:
        return "account has no email address"
    try:
        send_mail(
            subject,
            body,
            getattr(settings, "DEFAULT_FROM_EMAIL", branding.NOREPLY_EMAIL),
            [user.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error(
            "spend: email %r to user %s failed: %s",
            subject,
            user.pk,
            type(exc).__name__,
        )
        return f"{type(exc).__name__}: {exc}"[:2_000]
    return ""


def _alert_text(threshold: int, status: gate.AccountStatus) -> tuple[str, str]:
    spend = f"${status.spend_usd:.2f}"
    cap = f"${status.cap_usd:.2f}"
    url = f"{_site()}{gate.spend_settings_url()}"
    if threshold >= 100:
        subject = "SciTeX: monthly spend cap reached"
        lead = (
            f"Your SciTeX Cloud usage this month is {spend}, which has reached your "
            f"monthly cap of {cap}.\n\n"
            "New compute sessions and jobs are paused. Work that is already running "
            f"keeps going for {settings.SPEND_CONTROLS['running_grace_minutes']} "
            "minutes and is then stopped. Storage is not deleted; it becomes "
            "read-only until next month or until you raise your cap."
        )
    else:
        subject = f"SciTeX: {threshold}% of your monthly spend cap used"
        lead = (
            f"Your SciTeX Cloud usage this month is {spend}, {threshold}% of your "
            f"monthly cap of {cap}. Nothing has been paused."
        )
    provisional = (
        "\n\nThese figures are provisional: they are computed from launch and "
        "storage records until full usage metering is live."
        if status.snapshot.provisional
        else ""
    )
    body = f"{lead}{provisional}\n\nView usage or change your cap: {url}\n"
    return subject, body


def evaluate_alerts(user, status: gate.AccountStatus) -> list:
    """Create (once per month) and send the alerts the current level crosses."""
    from ..models import SpendAlert

    crossed = [t for t in SpendAlert.THRESHOLDS if int(status.level) >= t]
    created = []
    for threshold in crossed:
        try:
            with transaction.atomic():
                alert, is_new = SpendAlert.objects.get_or_create(
                    user=user,
                    period=status.snapshot.period,
                    threshold=threshold,
                    defaults={"spend_usd": status.spend_usd, "cap_usd": status.cap_usd},
                )
        except IntegrityError:  # a concurrent sweep created it
            continue
        if not is_new:
            continue
        created.append(alert)
    # One email for the HIGHEST newly crossed threshold: crossing 50 and 80 in
    # one sweep is one event for the reader, not two mails.
    if created:
        top = max(created, key=lambda a: a.threshold)
        subject, body = _alert_text(top.threshold, status)
        error = send_account_email(user, subject, body)
        now = timezone.now()
        for alert in created:
            alert.emailed_at = now if not error and alert is top else None
            alert.email_error = error if alert is top else "covered by the higher alert"
            alert.save(update_fields=["emailed_at", "email_error"])
    return created


def unread_alerts(user):
    from ..models import SpendAlert
    from .usage import period_bounds

    period, _, _ = period_bounds()
    return SpendAlert.objects.filter(user=user, period=period, read_at__isnull=True)


def mark_read(user) -> int:
    return unread_alerts(user).update(read_at=timezone.now())


__all__ = ["evaluate_alerts", "mark_read", "send_account_email", "unread_alerts"]
