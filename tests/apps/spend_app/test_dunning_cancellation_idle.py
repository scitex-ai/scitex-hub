"""Failed-payment dunning (through the real webhook handler), 30-day
cancellation (through a hand-rolled Stripe fake) and the idle reaper."""

import threading
from datetime import timedelta

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db


def _invoice_event(event_id, event_type, customer="cus_test_1"):
    return {
        "id": event_id,
        "type": event_type,
        "livemode": False,
        "data": {"object": {"id": "in_1", "customer": customer, "attempt_count": 1}},
    }


def _handle(event):
    from apps.infra.public_app.services.stripe_provider import StripeBillingProvider

    StripeBillingProvider(secret_key="").handle_event(event)


def _state(user):
    from apps.infra.spend_app.models import BillingAccountState

    return BillingAccountState.objects.get(user=user)


# ---------------------------------------------------------------- dunning


def test_a_failed_payment_starts_the_grace_period(user, subscription):
    # Arrange
    event = _invoice_event("evt_fail_1", "invoice.payment_failed")
    # Act
    _handle(event)
    # Assert
    assert _state(user).state == "past_due"


def test_the_grace_period_length_comes_from_settings(user, subscription, settings):
    # Arrange
    settings.SPEND_CONTROLS = {**settings.SPEND_CONTROLS, "payment_grace_days": 7}
    # Act
    _handle(_invoice_event("evt_fail_1", "invoice.payment_failed"))
    row = _state(user)
    # Assert
    assert (row.grace_until - row.past_due_since) == timedelta(days=7)


def test_a_replayed_failure_event_sends_only_one_reminder(
    user, subscription, mailoutbox
):
    # Arrange
    event = _invoice_event("evt_fail_1", "invoice.payment_failed")
    # Act
    _handle(event)
    _handle(event)
    # Assert
    assert len(mailoutbox) == 1


def test_reminders_follow_the_configured_days(user, subscription, mailoutbox):
    # Arrange
    from apps.infra.spend_app.services import dunning

    _handle(_invoice_event("evt_fail_1", "invoice.payment_failed"))
    day4 = _state(user).past_due_since + timedelta(days=4)
    # Act
    dunning.sweep_account(user, now=day4)
    # Assert: day 0 at once, day 3 by day 4
    assert _state(user).reminders_sent == 2


def test_the_account_is_restricted_when_the_grace_period_ends(user, subscription):
    # Arrange
    from apps.infra.spend_app.services import dunning

    _handle(_invoice_event("evt_fail_1", "invoice.payment_failed"))
    after = _state(user).grace_until + timedelta(minutes=1)
    # Act
    dunning.sweep_account(user, now=after)
    # Assert
    assert _state(user).state == "restricted"


def test_a_restricted_account_cannot_start_compute(user, subscription):
    # Arrange
    from apps.infra.spend_app.services import dunning, gate

    _handle(_invoice_event("evt_fail_1", "invoice.payment_failed"))
    dunning.sweep_account(user, now=_state(user).grace_until + timedelta(minutes=1))
    # Act
    call = lambda: gate.require_compute(user)  # noqa: E731
    # Assert
    with pytest.raises(gate.Refused, match="restricted"):
        call()


def test_restriction_never_deletes_the_workload_history(user, subscription, workload):
    # Arrange
    from apps.infra.spend_app.models import WorkloadSession
    from apps.infra.spend_app.services import dunning

    workload(hours=1.0)
    _handle(_invoice_event("evt_fail_1", "invoice.payment_failed"))
    # Act
    dunning.sweep_account(user, now=_state(user).grace_until + timedelta(minutes=1))
    # Assert
    assert WorkloadSession.objects.filter(user=user).count() == 1


def test_a_successful_payment_restores_a_restricted_account(user, subscription):
    # Arrange
    from apps.infra.spend_app.services import dunning

    _handle(_invoice_event("evt_fail_1", "invoice.payment_failed"))
    dunning.sweep_account(user, now=_state(user).grace_until + timedelta(minutes=1))
    # Act
    _handle(_invoice_event("evt_paid_1", "invoice.paid"))
    # Assert
    assert _state(user).state == "good"


def test_every_state_change_is_logged_append_only(user, subscription):
    # Arrange
    from apps.infra.spend_app.models import BillingAccountEvent

    _handle(_invoice_event("evt_fail_1", "invoice.payment_failed"))
    event = BillingAccountEvent.objects.get(kind="payment_failed")
    event.kind = "tampered"
    # Act
    call = event.save
    # Assert
    with pytest.raises(ValueError, match="append-only"):
        call()


# ---------------------------------------------------------------- cancellation


def test_cancellation_within_30_days_invoices_actual_usage_then_cancels_now(
    user, subscription, workload, fake_provider
):
    # Arrange
    from apps.infra.spend_app.services import cancellation

    workload(cpus=2, hours=1.0)  # $0.10 actual usage
    # Act
    cancellation.cancel_with_actual_usage(user, provider=fake_provider)
    # Assert
    assert [
        (name, kw.get("amount"), kw.get("invoice_now"))
        for name, kw in fake_provider.stripe.calls
    ] == [
        ("InvoiceItem.create", 10, None),
        ("Subscription.cancel", None, True),
    ]


def test_cancellation_prorates_the_plan_fee(user, subscription, fake_provider):
    # Arrange
    from apps.infra.spend_app.services import cancellation

    # Act
    cancellation.cancel_with_actual_usage(user, provider=fake_provider)
    cancel_kwargs = dict(fake_provider.stripe.calls)["Subscription.cancel"]
    # Assert
    assert cancel_kwargs["prorate"] is True


def test_cancellation_moves_the_account_back_to_the_free_plan(
    user, subscription, fake_provider
):
    # Arrange
    from apps.infra.spend_app.services import cancellation, catalog

    # Act
    cancellation.cancel_with_actual_usage(user, provider=fake_provider)
    # Assert
    assert catalog.plan_id_for(user) == "subscription-free"


def test_cancellation_is_refused_after_the_30_day_window(
    user, subscription, fake_provider
):
    # Arrange
    from apps.infra.spend_app.services import cancellation

    subscription.trial_start = timezone.now() - timedelta(days=31)
    subscription.save()
    # Act
    call = lambda: cancellation.cancel_with_actual_usage(user, provider=fake_provider)  # noqa: E731
    # Assert
    with pytest.raises(cancellation.CancellationRefused, match="window has closed"):
        call()


def test_cancellation_never_runs_against_a_live_stripe_key(user, subscription):
    # Arrange
    from apps.infra.spend_app.services import cancellation

    from .conftest import FakeProvider

    live = FakeProvider(secret_key="sk_live_fake")  # pragma: allowlist secret
    # Act
    call = lambda: cancellation.cancel_with_actual_usage(user, provider=live)  # noqa: E731
    # Assert
    with pytest.raises(cancellation.CancellationRefused, match="TEST mode"):
        call()


# ---------------------------------------------------------------- idle reaper


class _FakePTY:
    def __init__(self, username, last_activity):
        self.pty_id = f"pty-{username}"
        self.username = username
        self.last_activity = last_activity
        self.client_socket = object()
        self.closed = False

    def close(self):
        self.closed = True


class _FakeBroker:
    def __init__(self, ptys):
        self.lock = threading.Lock()
        self.sessions = {p.pty_id: p for p in ptys}
        self.session_index = {}
        self.shells = {}
        self.shell_index = {}
        self.alloc_index = {}
        self.allocations = {}
        self.sent = []

    def _send_message(self, sock, msg):
        self.sent.append(msg)


def _reaper(broker, now):
    from apps.infra.spend_app.services.policy import Run, RunningVerdict
    from apps.workspace.console_app.services.terminal_broker.idle_reaper import (
        IdleReaper,
    )

    return IdleReaper(
        broker, clock=lambda: now, verdict_fn=lambda u: RunningVerdict(Run.RUN)
    )


def test_an_idle_terminal_is_stopped_after_the_idle_limit(user, workload):
    # Arrange
    now = 10_000.0
    pty = _FakePTY(user.username, last_activity=now - 31 * 60)
    workload(open_=True)
    # Act
    _reaper(_FakeBroker([pty]), now).check_once()
    # Assert
    assert pty.closed


def test_the_idle_stop_closes_the_allocation_record_as_idle(user, workload):
    # Arrange
    from apps.infra.spend_app.models import WorkloadSession

    now = 10_000.0
    row = workload(open_=True)
    # Act
    _reaper(_FakeBroker([_FakePTY(user.username, now - 31 * 60)]), now).check_once()
    # Assert
    assert WorkloadSession.objects.get(pk=row.pk).stop_reason == "idle"


def test_an_idle_terminal_is_warned_before_it_is_stopped(user, workload):
    # Arrange
    now = 10_000.0
    broker = _FakeBroker([_FakePTY(user.username, now - 26 * 60)])
    workload(open_=True)
    # Act
    _reaper(broker, now).check_once()
    # Assert
    assert len(broker.sent) == 1


def test_a_terminal_that_is_still_printing_is_not_idle(user, workload):
    # Arrange
    now = 10_000.0
    pty = _FakePTY(user.username, last_activity=now - 10)
    workload(open_=True)
    # Act
    _reaper(_FakeBroker([pty]), now).check_once()
    # Assert
    assert not pty.closed


def test_an_allocation_record_with_no_live_session_is_closed_as_lost(user, workload):
    # Arrange
    from apps.infra.spend_app.models import WorkloadSession

    row = workload(open_=True)
    # Act
    _reaper(_FakeBroker([]), 10_000.0).check_once()
    # Assert
    assert WorkloadSession.objects.get(pk=row.pk).stop_reason == "lost"
