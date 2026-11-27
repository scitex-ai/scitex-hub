"""Failed-payment handling, driven by the signed Stripe webhook.

``invoice.payment_failed``   good -> past_due, grace starts (reminder #1 at once)
``invoice.paid`` /
``invoice.payment_succeeded`` past_due|restricted -> good
sweep (Celery beat)          sends the remaining reminders; at the end of the
                             grace period past_due -> restricted

Restricted = read-only and no new compute (see :mod:`.policy`). NOTHING here
deletes data, at any step. Every transition writes a ``BillingAccountEvent``.

The webhook is already verified, livemode-checked and claimed exactly once by
``public_app.views.billing.stripe_webhook``; these handlers are additionally
idempotent on the provider event id, so a replay cannot send a second mail.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import notify

logger = logging.getLogger("scitex")


def _field(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def user_for_customer(customer_id: str, *, metadata=None):
    """Map a provider customer to the Hub account, via rows we wrote."""
    from django.contrib.auth import get_user_model

    from apps.infra.public_app.models import PaymentMethod, PlanSubscription

    User = get_user_model()
    user_pk = _field(metadata or {}, "user_pk")
    if user_pk:
        user = User.objects.filter(pk=int(user_pk)).first()
        if user is not None:
            return user
    if not customer_id:
        return None
    sub = PlanSubscription.objects.filter(provider_customer_id=customer_id).first()
    if sub is not None:
        return sub.user
    card = PaymentMethod.objects.filter(stripe_customer_id=customer_id).first()
    if card is not None:
        return card.user
    try:
        from apps.infra.public_app.billing_models import BillingSetupSession

        setup = BillingSetupSession.objects.filter(
            stripe_customer_id=customer_id
        ).first()
    except Exception:  # pragma: no cover
        setup = None
    return setup.user if setup is not None else None


def _state_row(user):
    from ..models import BillingAccountState

    row, _ = BillingAccountState.objects.select_for_update().get_or_create(user=user)
    return row


def _log(user, kind, *, from_state="", to_state="", event_id="", **detail):
    from ..models import BillingAccountEvent

    BillingAccountEvent.objects.create(
        user=user,
        kind=kind,
        from_state=from_state,
        to_state=to_state,
        provider_event_id=event_id or "",
        detail=detail,
    )


def _already_applied(user, kind, event_id) -> bool:
    from ..models import BillingAccountEvent

    return (
        bool(event_id)
        and BillingAccountEvent.objects.filter(
            user=user, kind=kind, provider_event_id=event_id
        ).exists()
    )


def _billing_link() -> str:
    from .gate import billing_url

    return f"{getattr(settings, 'SITE_URL', '').rstrip('/')}{billing_url()}"


def _reminder_body(row, *, final: bool = False) -> tuple[str, str]:
    until = row.grace_until.strftime("%Y-%m-%d %H:%M UTC") if row.grace_until else ""
    if final:
        return (
            "SciTeX: account restricted after a failed payment",
            "We could not collect your SciTeX Cloud payment and the grace period "
            "has ended, so your account is now restricted: your data is kept and "
            "readable, but new compute and uploads are paused.\n\n"
            "Nothing has been deleted. Update your payment method to restore "
            f"full access: {_billing_link()}\n",
        )
    return (
        "SciTeX: your payment did not go through",
        "We could not collect your latest SciTeX Cloud payment. Your account "
        f"keeps working normally until {until}.\n\n"
        "If the payment is still outstanding then, the account becomes read-only "
        "(no new compute or uploads). Nothing is ever deleted.\n\n"
        f"Update your payment method: {_billing_link()}\n",
    )


def on_payment_failed(event) -> None:
    from ..models import BillingAccountState

    invoice = _field(_field(event, "data"), "object") or {}
    user = user_for_customer(
        _field(invoice, "customer") or "",
        metadata=_field(_field(invoice, "subscription_details") or {}, "metadata"),
    )
    if user is None:
        logger.warning("payment_failed %s: no mappable account", _field(event, "id"))
        return
    event_id = _field(event, "id", "")
    now = timezone.now()
    with transaction.atomic():
        if _already_applied(user, "payment_failed", event_id):
            return
        row = _state_row(user)
        before = row.state
        if row.state == BillingAccountState.State.GOOD:
            row.state = BillingAccountState.State.PAST_DUE
            row.past_due_since = now
            row.grace_until = now + timedelta(
                days=settings.SPEND_CONTROLS["payment_grace_days"]
            )
            row.reminders_sent = 0
            row.save()
        _log(
            user,
            "payment_failed",
            from_state=before,
            to_state=row.state,
            event_id=event_id,
            invoice=_field(invoice, "id", ""),
            attempt_count=_field(invoice, "attempt_count", 0),
        )
    sweep_account(user, now=now)


def on_payment_succeeded(event) -> None:
    from ..models import BillingAccountState

    invoice = _field(_field(event, "data"), "object") or {}
    user = user_for_customer(
        _field(invoice, "customer") or "",
        metadata=_field(_field(invoice, "subscription_details") or {}, "metadata"),
    )
    if user is None:
        return
    event_id = _field(event, "id", "")
    with transaction.atomic():
        if _already_applied(user, "payment_succeeded", event_id):
            return
        row = _state_row(user)
        before = row.state
        if row.state in (
            BillingAccountState.State.PAST_DUE,
            BillingAccountState.State.RESTRICTED,
        ):
            row.state = BillingAccountState.State.GOOD
            row.past_due_since = None
            row.grace_until = None
            row.reminders_sent = 0
            row.restricted_at = None
            row.save()
            restored = True
        else:
            restored = False
        _log(
            user,
            "payment_succeeded",
            from_state=before,
            to_state=row.state,
            event_id=event_id,
            invoice=_field(invoice, "id", ""),
        )
    if restored:
        notify.send_account_email(
            user,
            "SciTeX: payment received, account restored",
            "Thank you. Your payment went through and your SciTeX Cloud account "
            "is back to normal.\n",
        )


def sweep_account(user, *, now=None) -> str:
    """Send due reminders; restrict at the end of the grace period."""
    from ..models import BillingAccountState

    now = now or timezone.now()
    days = sorted(settings.SPEND_CONTROLS["payment_reminder_days"])
    with transaction.atomic():
        row = _state_row(user)
        if row.state != BillingAccountState.State.PAST_DUE:
            return row.state
        if row.grace_until and now >= row.grace_until:
            row.state = BillingAccountState.State.RESTRICTED
            row.restricted_at = now
            row.save()
            _log(user, "restricted", from_state="past_due", to_state="restricted")
            send = _reminder_body(row, final=True)
        else:
            due = [d for d in days if row.past_due_since + timedelta(days=d) <= now]
            if len(due) <= row.reminders_sent:
                return row.state
            row.reminders_sent = len(due)
            row.last_reminder_at = now
            row.save()
            _log(
                user,
                "payment_reminder",
                from_state="past_due",
                to_state="past_due",
                number=row.reminders_sent,
            )
            send = _reminder_body(row)
        state = row.state
    error = notify.send_account_email(user, *send)
    if error:
        logger.error("dunning mail for user %s not delivered: %s", user.pk, error)
    return state


def sweep_all(now=None) -> int:
    from ..models import BillingAccountState

    n = 0
    for row in BillingAccountState.objects.filter(
        state=BillingAccountState.State.PAST_DUE
    ):
        sweep_account(row.user, now=now)
        n += 1
    return n


__all__ = [
    "on_payment_failed",
    "on_payment_succeeded",
    "sweep_account",
    "sweep_all",
    "user_for_customer",
]
