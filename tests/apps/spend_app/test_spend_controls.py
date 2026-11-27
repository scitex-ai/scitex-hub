"""Spend controls against the real models: catalog caps, provisional usage,
alerts, the hard stop at enforcement points, quotas and the cap setting."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------- catalog


def test_plan_terms_read_the_default_and_maximum_cap_from_the_catalog():
    # Arrange
    from apps.infra.spend_app.services import catalog

    # Act
    terms = catalog.plan_terms("subscription-student")
    # Assert
    assert (terms.default_cap_usd, terms.max_cap_usd) == (Decimal("10"), Decimal("200"))


def test_an_account_without_a_subscription_is_on_the_free_plan(user):
    # Arrange
    from apps.infra.spend_app.services import catalog

    # Act
    plan = catalog.plan_id_for(user)
    # Assert
    assert plan == "subscription-free"


def test_every_subscription_row_states_a_spend_cap():
    # Arrange
    from apps.infra.public_app.pricing import load_pricing

    rows = [
        r
        for r in load_pricing()["published_prices"]
        if r.get("category") == "subscription"
    ]
    # Act
    missing = [r["id"] for r in rows if "spend_cap" not in r.get("attributes", {})]
    # Assert
    assert missing == []


def test_a_stored_cap_above_the_plan_maximum_is_clamped_to_the_maximum(
    user, cap, subscription
):
    # Arrange
    from apps.infra.spend_app.services import gate

    cap(999)
    # Act
    effective, _, _ = gate.effective_cap(user)
    # Assert
    assert effective == Decimal("200")


# ---------------------------------------------------------------- usage


def test_provisional_compute_is_billed_by_allocation(user, workload, subscription):
    # Arrange
    from apps.infra.spend_app.services import usage

    workload(cpus=2, memory_gb=8, hours=1.0)  # 2 CPU-units x 1 h at $0.05
    # Act
    snap = usage.current_snapshot(user, fresh=True)
    compute = next(l for l in snap.lines if l.resource == "compute")
    # Assert
    assert compute.amount_usd == Decimal("0.1000")


def test_memory_beyond_four_gib_per_core_is_billed_as_an_addon(
    user, workload, subscription
):
    # Arrange
    from apps.infra.spend_app.services import usage

    workload(cpus=1, memory_gb=6, hours=1.0)  # $0.05 + 2 GiB x $0.005
    # Act
    snap = usage.current_snapshot(user, fresh=True)
    compute = next(l for l in snap.lines if l.resource == "compute")
    # Assert
    assert compute.amount_usd == Decimal("0.0600")


def test_a_job_with_no_stop_record_is_charged_at_most_to_its_time_limit(
    user, workload, subscription
):
    # Arrange
    from apps.infra.spend_app.services import usage

    workload(cpus=1, hours=5.0, kind="job", open_=True, max_seconds=3_600)
    # Act
    snap = usage.current_snapshot(user, fresh=True)
    # Assert
    assert snap.cpu_hours.quantize(Decimal("0.01")) == Decimal("1.00")


def test_every_line_of_the_provisional_source_is_labelled_provisional(user):
    # Arrange
    from apps.infra.spend_app.services import usage

    # Act
    snap = usage.current_snapshot(user, fresh=True)
    # Assert
    assert all(line.provisional for line in snap.lines)


def test_storage_beyond_the_allowance_accrues_by_the_elapsed_share_of_the_month(
    user, subscription
):
    # Arrange
    from apps.infra.spend_app.services import usage

    _, start, end = usage.period_bounds()
    half = start + (end - start) / 2
    source = usage.ProvisionalUsageSource(
        storage_bytes_fn=lambda u: (32 + 100) * usage.GIB,  # 100 GB over
        now_fn=lambda: half,
    )
    # Act
    snap = source.snapshot(user, start=start, end=end)
    storage = next(l for l in snap.lines if l.resource == "storage")
    # Assert: 100 GB x $0.03 x ~half a month
    assert Decimal("1.40") < storage.amount_usd < Decimal("1.60")


# ---------------------------------------------------------------- alerts


def test_alerts_are_created_once_per_period_per_threshold(
    user, cap, workload, subscription
):
    # Arrange
    from apps.infra.spend_app.models import SpendAlert
    from apps.infra.spend_app.services import enforcement

    cap("0.10")
    workload(cpus=2, hours=0.85)  # $0.085 = 85 %
    # Act
    enforcement.sweep_user(user)
    enforcement.sweep_user(user)
    # Assert
    assert sorted(SpendAlert.objects.values_list("threshold", flat=True)) == [50, 80]


def test_one_email_is_sent_for_the_highest_newly_crossed_threshold(
    user, cap, workload, subscription, mailoutbox
):
    # Arrange
    from apps.infra.spend_app.services import enforcement

    cap("0.10")
    workload(cpus=2, hours=0.85)
    # Act
    enforcement.sweep_user(user)
    # Assert
    assert [m.subject for m in mailoutbox] == [
        "SciTeX: 80% of your monthly spend cap used"
    ]


def test_the_100_percent_email_names_the_grace_window_and_the_read_only_storage(
    user, cap, workload, subscription, mailoutbox
):
    # Arrange
    from apps.infra.spend_app.services import enforcement

    cap("0.10")
    workload(cpus=2, hours=1.5)
    # Act
    enforcement.sweep_user(user)
    # Assert
    assert "read-only" in mailoutbox[0].body


def test_raising_the_cap_clears_the_alerts_the_new_cap_no_longer_crosses(
    client, user, cap, workload, subscription
):
    # Arrange
    from apps.infra.spend_app.models import SpendAlert
    from apps.infra.spend_app.services import enforcement

    cap("0.10")
    workload(cpus=2, hours=1.5)
    enforcement.sweep_user(user)
    client.force_login(user)
    # Act
    client.post(reverse("spend_app:set_cap"), {"monthly_cap_usd": "100"})
    # Assert
    assert SpendAlert.objects.filter(user=user).count() == 0


def test_setting_a_cap_above_the_plan_maximum_is_refused(client, user, subscription):
    # Arrange
    from apps.infra.spend_app.models import SpendControl

    client.force_login(user)
    # Act
    client.post(reverse("spend_app:set_cap"), {"monthly_cap_usd": "201"})
    # Assert
    assert not SpendControl.objects.filter(
        user=user, monthly_cap_usd__isnull=False
    ).exists()


def test_the_spend_page_shows_the_80_percent_alert(
    client, user, cap, workload, subscription
):
    # Arrange
    cap("0.10")
    workload(cpus=2, hours=0.85)
    client.force_login(user)
    # Act
    page = client.get(reverse("spend_app:settings"))
    # Assert
    assert b'data-spend-alert="80"' in page.content


# ---------------------------------------------------------------- hard stop


def test_job_submission_at_the_cap_is_refused_with_402_and_the_raise_cap_link(
    client, user, cap, workload, subscription
):
    # Arrange
    cap("0.10")
    workload(cpus=2, hours=1.5)
    client.force_login(user)
    # Act
    response = client.post(
        reverse("console_app:api_submit_job"),
        data='{"script_path": "/workspace/a.py"}',
        content_type="application/json",
    )
    # Assert
    assert (response.status_code, response.json()["raise_cap_url"]) == (
        402,
        reverse("spend_app:settings"),
    )


def test_platform_job_submission_at_the_cap_is_refused(
    user, cap, workload, subscription
):
    # Arrange
    from apps.infra.platform_app.services.jobqueue.executor import JobQueue
    from apps.infra.spend_app.services import gate

    cap("0.10")
    workload(cpus=2, hours=1.5)
    # Act
    call = lambda: JobQueue().submit("stats", "run", None, user)  # noqa: E731
    # Assert
    with pytest.raises(gate.Refused):
        call()


def test_storage_writes_are_read_only_at_the_cap(user, cap, workload, subscription):
    # Arrange
    from apps.infra.spend_app.decorators import storage_write

    cap("0.10")
    workload(cpus=2, hours=1.5)
    request = RequestFactory().post("/api/files/upload", HTTP_ACCEPT="application/json")
    request.user = user
    view = storage_write(lambda r: HttpResponse("written"))
    # Act
    response = view(request)
    # Assert
    assert response.status_code == 402


def test_storage_writes_are_allowed_under_the_cap(user, cap, subscription):
    # Arrange
    from apps.infra.spend_app.decorators import storage_write

    cap("10")
    request = RequestFactory().post("/api/files/upload", HTTP_ACCEPT="application/json")
    request.user = user
    view = storage_write(lambda r: HttpResponse("written"))
    # Act
    response = view(request)
    # Assert
    assert response.status_code == 200


def test_reattaching_to_a_running_terminal_is_allowed_during_the_grace_window(
    user, cap, workload, subscription
):
    # Arrange
    from apps.infra.spend_app.services import enforcement

    cap("0.10")
    workload(cpus=2, hours=1.5, open_=True)  # the open allocation IS the spend
    enforcement.sweep_user(user)  # fires the 100 % alert; grace starts now
    # Act
    result = enforcement.require_terminal(user)
    # Assert
    assert result is None


def test_a_new_terminal_at_the_cap_is_refused(user, cap, workload, subscription):
    # Arrange
    from apps.infra.spend_app.services import enforcement, gate

    cap("0.10")
    workload(cpus=2, hours=1.5)  # closed: no allocation is running
    # Act
    call = lambda: enforcement.require_terminal(user)  # noqa: E731
    # Assert
    with pytest.raises(gate.Refused, match="Spend controls"):
        call()


def test_running_jobs_are_stopped_when_the_grace_window_ends(
    user, cap, workload, subscription
):
    # Arrange
    from apps.infra.spend_app.models import SpendAlert, WorkloadSession
    from apps.infra.spend_app.services import enforcement

    cap("0.10")
    workload(cpus=2, hours=1.5)
    job = workload(cpus=1, hours=0.1, kind="job", open_=True)
    enforcement.sweep_user(user)
    SpendAlert.objects.filter(user=user, threshold=100).update(
        created_at=timezone.now() - timedelta(hours=1)
    )
    # Act
    enforcement.sweep_user(user)
    # Assert
    assert WorkloadSession.objects.get(pk=job.pk).stop_reason == "spend_cap"


# ---------------------------------------------------------------- quotas


def test_a_job_above_the_memory_quota_is_refused(user, subscription):
    # Arrange
    from apps.infra.spend_app.services import gate

    # Act
    call = lambda: gate.require_job(  # noqa: E731
        user, cpus=1, memory_gb=999, time_limit_seconds=60, partition="compute"
    )
    # Assert
    with pytest.raises(gate.Refused, match="memory"):
        call()


def test_a_user_quota_override_does_not_leak_into_other_users_defaults(
    user, django_user_model
):
    # Arrange
    from apps.workspace.console_app.models import UserQuota
    from config.settings.quotas import get_user_quotas

    UserQuota.objects.create(user=user, slurm_max_memory_gb_per_job=1)
    get_user_quotas(user)
    other = django_user_model.objects.create_user(
        username="other", password="pw-test-only",  # pragma: allowlist secret
    )
    # Act
    quotas = get_user_quotas(other)
    # Assert
    assert quotas["slurm"]["max_memory_gb_per_job"] != 1


def test_the_project_quota_refuses_a_project_beyond_the_limit(user):
    # Arrange
    from apps.infra.spend_app.services import gate
    from apps.workspace.console_app.models import UserQuota

    UserQuota.objects.create(user=user, max_projects=0)
    # Act
    call = lambda: gate.check_project_quota(user)  # noqa: E731
    # Assert
    with pytest.raises(gate.Refused, match="at most 0 projects"):
        call()


def test_an_upload_larger_than_the_per_file_quota_is_refused(user):
    # Arrange
    from apps.infra.spend_app.services import gate
    from apps.workspace.console_app.models import UserQuota

    UserQuota.objects.create(user=user, storage_file_upload_mb=1)
    # Act
    call = lambda: gate.check_storage_quota(  # noqa: E731
        user, incoming_sizes=[2 * 1_048_576]
    )
    # Assert
    with pytest.raises(gate.Refused, match="1 MB"):
        call()


# ---------------------------------------------------------------- migrations


@pytest.mark.django_db(transaction=True)
def test_the_spend_app_migration_reverses_and_reapplies_cleanly():
    # Arrange
    from django.core.management import call_command
    from django.db import connection

    call_command("migrate", "spend_app", "zero", verbosity=0)
    # Act
    call_command("migrate", "spend_app", verbosity=0)
    # Assert
    assert "spend_app_spendcontrol" in connection.introspection.table_names()
