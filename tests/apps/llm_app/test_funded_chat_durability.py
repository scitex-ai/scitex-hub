from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.db import close_old_connections
from django.test import override_settings

from apps.infra.auth_app.models import EmailVerification
from apps.infra.llm_app.funded_chat.config import load_funded_chat_config
from apps.infra.llm_app.funded_chat.provider import ProviderPreDispatchError
from apps.infra.llm_app.funded_chat.service import (
    FundedChatDenied,
    FundedChatService,
    ProviderResult,
)
from apps.infra.llm_app.models import (
    FundedChatDailyQuota,
    FundedChatDailySpend,
    FundedChatRequest,
)

FUNDED_SETTINGS = {
    "SCITEX_FUNDED_CHAT_ENABLED": True,
    "SCITEX_FUNDED_CHAT_PROVIDER": "deepseek",
    "SCITEX_FUNDED_CHAT_MODEL": "deepseek-chat",
    "SCITEX_FUNDED_CHAT_API_KEY": "not-read-by-test",
    "SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD": "5.00",
    "SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD": "3.00",
    "SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD": "0.05",
    "SCITEX_FUNDED_CHAT_REQUESTS_PER_MINUTE": 100,
    "SCITEX_FUNDED_CHAT_RESERVATION_LEASE_SECONDS": 60,
}
NOW = datetime(2026, 9, 17, 23, 59, 30, tzinfo=timezone.utc)


def _user(name: str) -> User:
    user = User.objects.create_user(
        username=name, email=f"{name}@example.com", password="unused"
    )
    EmailVerification.objects.create(user=user, email=user.email, is_verified=True)
    return user


def _service(now=NOW) -> FundedChatService:
    return FundedChatService(config=load_funded_chat_config(), now=lambda: now)


def _result(cost: str = "0.01") -> ProviderResult:
    return ProviderResult(
        text="answer",
        prompt_tokens=2,
        completion_tokens=3,
        provider_cost_usd=Decimal(cost),
    )


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
def test_known_pre_dispatch_failure_is_the_only_failure_that_releases_quota():
    user = _user("predispatch")

    def fail_before_send(config, body, dispatch_key):
        raise ProviderPreDispatchError("sanitized")

    with pytest.raises(FundedChatDenied):
        _service().execute(
            user,
            idempotency_key="pre-send",
            request_body=b'{"messages":[{"role":"user","content":"hi"}]}',
            provider_call=fail_before_send,
        )

    request = FundedChatRequest.objects.get(user=user)
    assert request.status == FundedChatRequest.STATUS_FAILED
    assert request.phase == FundedChatRequest.PHASE_PRE_DISPATCH
    assert request.reserved_subsidy_usd == 0
    assert FundedChatDailyQuota.objects.get(user=user).claimed_count == 0


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
@pytest.mark.parametrize(
    "failure",
    [TimeoutError("accepted then timeout"), ConnectionError("response lost")],
)
def test_ambiguous_post_dispatch_failure_retains_reservation_for_reconciliation(
    failure,
):
    user = _user(type(failure).__name__.lower())

    def ambiguous(config, body, dispatch_key):
        raise failure

    with pytest.raises(FundedChatDenied):
        _service().execute(
            user,
            idempotency_key="ambiguous",
            request_body=b'{"messages":[{"role":"user","content":"hi"}]}',
            provider_call=ambiguous,
        )

    request = FundedChatRequest.objects.get(user=user)
    assert request.status == FundedChatRequest.STATUS_RECONCILIATION_REQUIRED
    assert request.phase == FundedChatRequest.PHASE_DISPATCHED
    assert request.reserved_subsidy_usd == Decimal("0.050000")
    assert FundedChatDailyQuota.objects.get(user=user).claimed_count == 1
    spend = FundedChatDailySpend.objects.get(
        day=request.day, scope=FundedChatDailySpend.GLOBAL_SCOPE
    )
    assert spend.reserved_subsidy_usd == Decimal("0.050000")
    assert spend.subsidy_cost_usd == 0


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
def test_cancellation_after_dispatch_is_propagated_but_never_restores_quota():
    user = _user("cancelled")

    def cancelled(config, body, dispatch_key):
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        _service().execute(
            user,
            idempotency_key="cancelled",
            request_body=b'{"messages":[{"role":"user","content":"hi"}]}',
            provider_call=cancelled,
        )

    request = FundedChatRequest.objects.get(user=user)
    assert request.status == FundedChatRequest.STATUS_RECONCILIATION_REQUIRED
    assert request.reserved_subsidy_usd == Decimal("0.050000")
    assert FundedChatDailyQuota.objects.get(user=user).claimed_count == 1


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
def test_sub_micro_actual_cost_is_rounded_up_and_cannot_disappear():
    user = _user("submicro")

    result = _service().execute(
        user,
        idempotency_key="submicro",
        request_body=b'{"messages":[{"role":"user","content":"hi"}]}',
        provider_call=lambda config, body, key: _result("0.0000001"),
    )

    assert result.provider_cost_usd == Decimal("0.000001")
    request = FundedChatRequest.objects.get(user=user)
    assert request.provider_cost_usd == Decimal("0.000001")
    spend = FundedChatDailySpend.objects.get(
        day=request.day, scope=FundedChatDailySpend.GLOBAL_SCOPE
    )
    assert spend.provider_cost_usd == Decimal("0.000001")


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
def test_actual_over_reservation_is_recorded_and_trips_fail_closed():
    user = _user("overshoot")

    with pytest.raises(FundedChatDenied) as denied:
        _service().execute(
            user,
            idempotency_key="overshoot",
            request_body=b'{"messages":[{"role":"user","content":"hi"}]}',
            provider_call=lambda config, body, key: _result("0.06"),
        )

    assert denied.value.category == "provider_outage"
    request = FundedChatRequest.objects.get(user=user)
    assert request.status == FundedChatRequest.STATUS_ACCOUNTING_ANOMALY
    assert request.provider_cost_usd == Decimal("0.060000")
    assert request.reserved_subsidy_usd == 0
    spend = FundedChatDailySpend.objects.get(
        day=request.day, scope=FundedChatDailySpend.GLOBAL_SCOPE
    )
    assert spend.provider_cost_usd == Decimal("0.060000")
    assert spend.subsidy_cost_usd == Decimal("0.060000")


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
def test_post_provider_crash_leaves_durable_result_for_reconciliation(monkeypatch):
    user = _user("postcrash")
    service = _service()
    original = service._finalize_succeeded_request

    def crash_after_durable_result(request_id):
        raise RuntimeError("simulated process death")

    monkeypatch.setattr(
        service, "_finalize_succeeded_request", crash_after_durable_result
    )
    with pytest.raises(RuntimeError, match="simulated process death"):
        service.execute(
            user,
            idempotency_key="postcrash",
            request_body=b'{"messages":[{"role":"user","content":"hi"}]}',
            provider_call=lambda config, body, key: _result("0.01"),
        )

    request = FundedChatRequest.objects.get(user=user)
    assert request.status == FundedChatRequest.STATUS_PROVIDER_SUCCEEDED
    assert request.provider_cost_usd == Decimal("0.010000")
    monkeypatch.setattr(service, "_finalize_succeeded_request", original)
    assert service.reconcile_stale_requests() == 1
    request.refresh_from_db()
    assert request.status == FundedChatRequest.STATUS_SUCCEEDED
    assert request.reserved_subsidy_usd == 0


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
def test_expired_pre_dispatch_lease_releases_safely():
    user = _user("lease")
    service = _service()
    reserved = service.reserve(user, idempotency_key="lease", request_body=b"body")
    FundedChatRequest.objects.filter(pk=reserved.request.pk).update(
        lease_expires_at=NOW - timedelta(seconds=1)
    )

    assert service.reconcile_stale_requests() == 1
    request = FundedChatRequest.objects.get(pk=reserved.request.pk)
    assert request.status == FundedChatRequest.STATUS_FAILED
    assert request.reserved_subsidy_usd == 0
    assert FundedChatDailyQuota.objects.get(user=user).claimed_count == 0


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
def test_expired_dispatched_lease_is_conservatively_charged():
    user = _user("dispatched-lease")
    service = _service()
    reserved = service.reserve(
        user, idempotency_key="dispatched-lease", request_body=b"body"
    )
    service._mark_dispatching(reserved.request.pk)
    FundedChatRequest.objects.filter(pk=reserved.request.pk).update(
        lease_expires_at=NOW - timedelta(seconds=1)
    )

    assert service.reconcile_stale_requests() == 1
    request = FundedChatRequest.objects.get(pk=reserved.request.pk)
    assert request.status == FundedChatRequest.STATUS_RECONCILED
    assert request.phase == FundedChatRequest.PHASE_RECONCILED
    assert request.provider_cost_usd == Decimal("0.050000")
    assert request.reserved_subsidy_usd == 0
    spend = FundedChatDailySpend.objects.get(
        day=request.day, scope=FundedChatDailySpend.GLOBAL_SCOPE
    )
    assert spend.provider_cost_usd == Decimal("0.050000")
    assert spend.reserved_subsidy_usd == 0


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
def test_same_idempotency_key_concurrency_never_double_dispatches():
    user = _user("samekey")
    entered = threading.Event()
    release = threading.Event()
    calls = []

    def provider(config, body, dispatch_key):
        calls.append(dispatch_key)
        entered.set()
        assert release.wait(timeout=10)
        return _result()

    def run_first():
        close_old_connections()
        try:
            return _service().execute(
                User.objects.get(pk=user.pk),
                idempotency_key="same-key",
                request_body=b"same-body",
                provider_call=provider,
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(run_first)
        assert entered.wait(timeout=10)
        with pytest.raises(FundedChatDenied):
            _service().execute(
                user,
                idempotency_key="same-key",
                request_body=b"same-body",
                provider_call=provider,
            )
        release.set()
        assert first.result(timeout=10).text == "answer"

    assert len(calls) == 1
    assert FundedChatRequest.objects.filter(user=user).count() == 1


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
def test_durable_provider_result_replay_after_restart_finalizes_without_redispatch():
    user = _user("provider-result-replay")
    before_restart = _service()
    reservation = before_restart.reserve(
        user, idempotency_key="provider-result", request_body=b"same-body"
    )
    before_restart._mark_dispatching(reservation.request.pk)
    before_restart._persist_provider_result(reservation.request.pk, _result())
    provider_calls = []

    result = _service().execute(
        user,
        idempotency_key="provider-result",
        request_body=b"same-body",
        provider_call=lambda *args: provider_calls.append(args) or _result(),
    )

    assert result == _result()
    assert provider_calls == []
    request = FundedChatRequest.objects.get(pk=reservation.request.pk)
    assert request.status == FundedChatRequest.STATUS_SUCCEEDED


@pytest.mark.django_db(transaction=True)
@override_settings(
    **{
        **FUNDED_SETTINGS,
        "SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD": "0.05",
        "SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD": "0.05",
    }
)
def test_cross_user_global_and_provider_cap_contention_allows_only_one_reservation():
    users = [_user("cap-a"), _user("cap-b")]
    barrier = threading.Barrier(2)

    def reserve(user_id, number):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            _service().reserve(
                User.objects.get(pk=user_id),
                idempotency_key=f"cap-{number}",
                request_body=b"body",
            )
            return "reserved"
        except FundedChatDenied as exc:
            return exc.category
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(lambda args: reserve(*args), [(users[0].pk, 0), (users[1].pk, 1)])
        )

    assert sorted(outcomes) == ["insufficient_balance", "reserved"]
    global_spend = FundedChatDailySpend.objects.get(
        day=NOW.date(), scope=FundedChatDailySpend.GLOBAL_SCOPE
    )
    provider_spend = FundedChatDailySpend.objects.get(day=NOW.date(), scope="deepseek")
    assert global_spend.reserved_subsidy_usd == Decimal("0.050000")
    assert provider_spend.reserved_subsidy_usd == Decimal("0.050000")


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
def test_utc_day_boundary_uses_utc_not_server_locale():
    user = _user("utc-boundary")
    before = _service(datetime(2026, 9, 17, 23, 59, 59, tzinfo=timezone.utc))
    after = _service(datetime(2026, 9, 18, 0, 0, 0, tzinfo=timezone.utc))

    before.reserve(user, idempotency_key="before", request_body=b"body")
    after.reserve(user, idempotency_key="after", request_body=b"body")

    assert list(
        FundedChatDailyQuota.objects.filter(user=user)
        .order_by("day")
        .values_list("day", "claimed_count")
    ) == [(NOW.date(), 1), ((NOW + timedelta(days=1)).date(), 1)]


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
@pytest.mark.parametrize(
    "status,phase",
    [
        (FundedChatRequest.STATUS_DISPATCHING, FundedChatRequest.PHASE_DISPATCHED),
        (
            FundedChatRequest.STATUS_RECONCILIATION_REQUIRED,
            FundedChatRequest.PHASE_DISPATCHED,
        ),
        (FundedChatRequest.STATUS_RECONCILED, FundedChatRequest.PHASE_RECONCILED),
        (
            FundedChatRequest.STATUS_ACCOUNTING_ANOMALY,
            FundedChatRequest.PHASE_RESPONSE_RECEIVED,
        ),
    ],
)
def test_post_dispatch_same_key_replay_after_restart_and_expired_lease_never_redispatches(
    status, phase
):
    user = _user(f"replay-{status}")
    before_restart = _service()
    reservation = before_restart.reserve(
        user, idempotency_key="durable-key", request_body=b"same-body"
    )
    before_restart._mark_dispatching(reservation.request.pk)
    FundedChatRequest.objects.filter(pk=reservation.request.pk).update(
        status=status,
        phase=phase,
        lease_expires_at=NOW - timedelta(days=1),
    )
    provider_calls = []

    after_restart = _service(NOW + timedelta(days=1))
    with pytest.raises(FundedChatDenied):
        after_restart.execute(
            user,
            idempotency_key="durable-key",
            request_body=b"same-body",
            provider_call=lambda *args: provider_calls.append(args) or _result(),
        )

    assert provider_calls == []
    request = FundedChatRequest.objects.get(pk=reservation.request.pk)
    assert (request.status, request.phase) == (status, phase)


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
def test_reconciler_fails_closed_before_touching_a_colliding_spend_scope():
    user = _user("collision-guard")
    service = _service()
    reservation = service.reserve(
        user, idempotency_key="collision", request_body=b"body"
    )
    service._mark_dispatching(reservation.request.pk)
    FundedChatRequest.objects.filter(pk=reservation.request.pk).update(
        provider=FundedChatDailySpend.GLOBAL_SCOPE,
        lease_expires_at=NOW - timedelta(seconds=1),
    )
    global_spend = FundedChatDailySpend.objects.get(
        day=NOW.date(), scope=FundedChatDailySpend.GLOBAL_SCOPE
    )
    before = (
        global_spend.reserved_subsidy_usd,
        global_spend.provider_cost_usd,
        global_spend.subsidy_cost_usd,
    )

    with pytest.raises(FundedChatDenied):
        service.reconcile_stale_requests()

    global_spend.refresh_from_db()
    assert (
        global_spend.reserved_subsidy_usd,
        global_spend.provider_cost_usd,
        global_spend.subsidy_cost_usd,
    ) == before
    request = FundedChatRequest.objects.get(pk=reservation.request.pk)
    assert request.status == FundedChatRequest.STATUS_DISPATCHING


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
def test_reconciler_never_mutates_a_ledger_quarantined_for_operator_repair():
    user = _user("repair-ledger-guard")
    service = _service()
    reservation = service.reserve(
        user, idempotency_key="repair-ledger", request_body=b"body"
    )
    service._mark_dispatching(reservation.request.pk)
    FundedChatRequest.objects.filter(pk=reservation.request.pk).update(
        lease_expires_at=NOW - timedelta(seconds=1)
    )
    global_spend = FundedChatDailySpend.objects.get(
        day=NOW.date(), scope=FundedChatDailySpend.GLOBAL_SCOPE
    )
    global_spend.requires_operator_repair = True
    global_spend.operator_repair_metadata = {"accounting_state": "unknown"}
    global_spend.save(
        update_fields=["requires_operator_repair", "operator_repair_metadata"]
    )
    before = (
        global_spend.reserved_subsidy_usd,
        global_spend.provider_cost_usd,
        global_spend.subsidy_cost_usd,
    )

    with pytest.raises(FundedChatDenied):
        service.reconcile_stale_requests()

    global_spend.refresh_from_db()
    assert (
        global_spend.reserved_subsidy_usd,
        global_spend.provider_cost_usd,
        global_spend.subsidy_cost_usd,
    ) == before
