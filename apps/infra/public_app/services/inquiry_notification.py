#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tell the operator about a new inquiry, through scitex-notification.

WHY (scitex-hub#1235). Prod held 8 inquiries and all 8 were unhandled, because
nobody ever heard about them. Each view mailed ``SERVICES_INQUIRY_EMAIL``
with Django's ``send_mail`` through the Hub's own SMTP account. That account's
login was refused (SMTP 535, scitex-hub#1234). The failure was logged at
WARNING to a file, so a lead could only be found by someone remembering to open
the admin.

WHAT CHANGED.
  * ONE function for both forms (/services/ and /contact/), instead of two
    near-copies that drifted.
  * The mail goes through ``scitex_notification.send_email``. That is the same
    rail the fleet uses for agent -> operator mail, so there is no new sender.
    Its identity is passed in explicitly, as one coherent set (see
    :func:`_identity`), because the package's env fallbacks resolve the sender,
    password and host independently and could pair one account's address with
    another's password.
  * The OUTCOME is recorded on the row (``notified_at`` / ``notify_error``),
    so the admin list shows which leads the operator was actually told about.
    The DB row is still written first and stays the record of truth; a failed
    notification never loses an inquiry.

The body carries the inquirer's details because the operator needs them to
reply. Logs carry only the row id and the exception CLASS, never personal data.
"""

from __future__ import annotations

import logging
import os

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

__all__ = [
    "dispatch_inquiry_notification",
    "notification_recipients",
    "notify_operator_of_inquiry",
]


def notification_recipients() -> list[str]:
    """Who is told: the operator first, then the shared inquiry inbox.

    Duplicates and blanks are dropped, and order is kept so the operator is
    always the first address.
    """
    candidates = [
        getattr(settings, "INQUIRY_NOTIFY_TO", ""),
        getattr(settings, "SERVICES_INQUIRY_EMAIL", ""),
    ]
    seen: list[str] = []
    for raw in candidates:
        for addr in (raw or "").split(","):
            addr = addr.strip()
            if addr and addr.lower() not in {s.lower() for s in seen}:
                seen.append(addr)
    return seen


def _identity() -> dict:
    """One coherent SMTP identity for scitex-notification.

    The scitex-notification account (``SCITEX_NOTIFICATION_EMAIL_*``, the
    agent -> operator route) is used when it is configured, as a complete set.
    Otherwise the Hub's own mail account is used, also as a complete set. The
    two are never mixed.
    """
    env = os.environ
    if env.get("SCITEX_NOTIFICATION_EMAIL_FROM") and env.get(
        "SCITEX_NOTIFICATION_EMAIL_PASSWORD"
    ):
        return {
            "from_addr": env["SCITEX_NOTIFICATION_EMAIL_FROM"],
            "password": env["SCITEX_NOTIFICATION_EMAIL_PASSWORD"],
            "smtp_host": env.get("SCITEX_NOTIFICATION_EMAIL_SMTP_HOST")
            or settings.EMAIL_HOST,
            "smtp_port": int(
                env.get("SCITEX_NOTIFICATION_EMAIL_SMTP_PORT") or settings.EMAIL_PORT
            ),
        }
    return {
        "from_addr": settings.DEFAULT_FROM_EMAIL,
        "password": settings.EMAIL_HOST_PASSWORD,
        "smtp_host": settings.EMAIL_HOST,
        "smtp_port": int(settings.EMAIL_PORT),
    }


def _admin_url(inquiry) -> str:
    from django.urls import reverse

    base = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    path = reverse("admin:public_app_serviceinquiry_change", args=[inquiry.pk])
    return f"{base}{path}"


def _message(inquiry, *, source: str, reply_to: str) -> tuple[str, str]:
    subject = f"[SciTeX inquiry] {source}: {inquiry.name}"
    body = (
        f"A new inquiry arrived on SciTeX Hub ({source}).\n"
        f"新しいお問い合わせがありました。\n\n"
        f"お名前 / Name: {inquiry.name}\n"
        f"ご連絡先 / Reply to: {reply_to or '-'}\n"
        f"ご所属 / Affiliation: {inquiry.affiliation or '-'}\n"
        f"種別・ご予算感 / Type or budget: {inquiry.budget or '-'}\n"
        f"受付日時 / Received: {inquiry.created_at:%Y-%m-%d %H:%M} UTC\n\n"
        f"ご相談内容 / Message:\n{inquiry.request}\n\n"
        f"Mark it handled once replied: {_admin_url(inquiry)}\n"
    )
    return subject, body


def _reply_address(inquiry) -> str:
    """/contact/ stores the reply address in ``affiliation``; /services/ has none."""
    value = (inquiry.affiliation or "").strip()
    return value if "@" in value and " " not in value else ""


def dispatch_inquiry_notification(inquiry, *, source: str) -> None:
    """Notify the operator once the inquiry row is committed.

    Queued on Celery so a slow mail server never holds the visitor's request.
    The task carries only the row id, never personal data. If the broker
    cannot be reached, the notification is sent inline instead: a broker
    outage must not silently swallow a lead.
    """
    from django.db import transaction

    def _send():
        from kombu.exceptions import OperationalError as BrokerError

        from apps.infra.public_app.tasks.inquiries import notify_service_inquiry

        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            # Eager mode runs tasks inline anyway. Calling the function
            # directly keeps Celery's Django fixup from closing this request's
            # database connection mid-request.
            notify_operator_of_inquiry(inquiry, source=source)
            return
        try:
            notify_service_inquiry.delay(inquiry.pk, source)
        except (BrokerError, OSError) as exc:  # broker down: send inline
            logger.warning(
                "ServiceInquiry %s: queue unavailable (%s), notifying inline",
                inquiry.pk,
                type(exc).__name__,
            )
            notify_operator_of_inquiry(inquiry, source=source)

    transaction.on_commit(_send)


def notify_operator_of_inquiry(inquiry, *, source: str, reply_to: str = "") -> bool:
    """Send the notification now, and record the outcome on the row.

    Returns True when the SMTP server accepted the message. Never raises: the
    inquiry is already stored, and the request that created it must not fail
    because a notification did.
    """
    from scitex_notification import send_email

    recipients = notification_recipients()
    if not recipients:
        inquiry.record_notification(ok=False, error="no recipient configured")
        logger.error(
            "ServiceInquiry %s stored; NO notification recipient set", inquiry.pk
        )
        return False

    reply_to = reply_to or _reply_address(inquiry)
    subject, body = _message(inquiry, source=source, reply_to=reply_to)
    try:
        send_email(to=", ".join(recipients), subject=subject, body=body, **_identity())
    except Exception as exc:  # noqa: BLE001 -- recorded on the row and logged
        inquiry.record_notification(ok=False, error=type(exc).__name__)
        logger.error(
            "ServiceInquiry %s stored but the operator notification FAILED (%s). "
            "Open the admin inquiry list; this lead has not been seen.",
            inquiry.pk,
            type(exc).__name__,
        )
        return False

    inquiry.record_notification(ok=True)
    logger.info(
        "ServiceInquiry %s: operator notified at %s", inquiry.pk, timezone.now()
    )
    return True


# EOF
