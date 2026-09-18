from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

MIGRATE_FROM = [("llm_app", "0006_fundedchatdailyspend_fundedchatdailyquota_and_more")]
MIGRATE_TO = [("llm_app", "0007_fundedchatrequest_dispatch_key_and_more")]


@pytest.fixture
def populated_funded_chat_0006(transactional_db):
    executor = MigrationExecutor(connection)
    executor.migrate(MIGRATE_FROM)
    request_ids: dict[str, int] = {}
    spend_ids: dict[str, int] = {}
    try:
        old_apps = executor.loader.project_state(MIGRATE_FROM).apps
        User = old_apps.get_model("auth", "User")
        Request = old_apps.get_model("llm_app", "FundedChatRequest")
        Spend = old_apps.get_model("llm_app", "FundedChatDailySpend")
        user = User.objects.create(username="migration-funded", password="unused")
        day = date(2026, 9, 17)

        def create_request(name: str, *, provider: str, status: str, **amounts):
            request = Request.objects.create(
                user=user,
                day=day,
                idempotency_key_hash=name.ljust(64, "0")[:64],
                request_hash=name.ljust(64, "1")[:64],
                provider=provider,
                model=f"{provider}/model",
                status=status,
                **amounts,
            )
            request_ids[name] = request.pk

        create_request(
            "reserved",
            provider="deepseek",
            status="reserved",
            reserved_subsidy_usd="0.05",
        )
        create_request(
            "succeeded",
            provider="deepseek",
            status="succeeded",
            provider_cost_usd="0.01",
            subsidy_cost_usd="0.01",
        )
        create_request("failed", provider="deepseek", status="failed")
        for status in ("reserved", "succeeded", "failed"):
            create_request(
                f"collision-{status}",
                provider="__global__",
                status=status,
                reserved_subsidy_usd="0.05" if status == "reserved" else "0",
                provider_cost_usd="0.01" if status == "succeeded" else "0",
                subsidy_cost_usd="0.01" if status == "succeeded" else "0",
            )
        create_request(
            "corrupt-request",
            provider="anthropic",
            status="succeeded",
            reserved_subsidy_usd="-0.01",
            provider_cost_usd="-0.02",
            subsidy_cost_usd="-0.03",
        )

        for scope, amounts in {
            "__global__": ("0.05", "0.50", "0.40"),
            "deepseek": ("0.05", "0.01", "0.01"),
            "anthropic": ("-0.10", "-0.20", "-0.30"),
        }.items():
            spend = Spend.objects.create(
                day=day,
                scope=scope,
                reserved_subsidy_usd=amounts[0],
                provider_cost_usd=amounts[1],
                subsidy_cost_usd=amounts[2],
            )
            spend_ids[scope] = spend.pk

        executor = MigrationExecutor(connection)
        executor.migrate(MIGRATE_TO)
        new_apps = executor.loader.project_state(MIGRATE_TO).apps
        yield new_apps, request_ids, spend_ids
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_populated_migration_quarantines_global_scope_collisions_and_corruption(
    populated_funded_chat_0006,
):
    apps, request_ids, spend_ids = populated_funded_chat_0006
    Request = apps.get_model("llm_app", "FundedChatRequest")
    Spend = apps.get_model("llm_app", "FundedChatDailySpend")

    reserved = Request.objects.get(pk=request_ids["reserved"])
    succeeded = Request.objects.get(pk=request_ids["succeeded"])
    failed = Request.objects.get(pk=request_ids["failed"])
    assert (reserved.status, reserved.phase) == ("reconcile_required", "dispatched")
    assert (succeeded.status, succeeded.phase) == ("succeeded", "response_received")
    assert (failed.status, failed.phase) == ("failed", "pre_dispatch")

    collisions = Request.objects.filter(provider="__global__").order_by("pk")
    assert collisions.count() == 3
    for request in collisions:
        assert request.status == "operator_repair_required"
        assert request.phase == "dispatched"
        assert request.reconciliation_required_at is not None
        assert request.operator_repair_metadata["reason"] == (
            "legacy_global_provider_scope_collision"
        )
        assert request.operator_repair_metadata["legacy_status"] in {
            "reserved",
            "succeeded",
            "failed",
        }

    global_spend = Spend.objects.get(pk=spend_ids["__global__"])
    assert global_spend.requires_operator_repair is True
    assert global_spend.operator_repair_metadata["accounting_state"] == "unknown"
    # Ambiguous accounting is retained verbatim; the migration does not guess.
    assert global_spend.provider_cost_usd == Decimal("0.500000")
    assert global_spend.subsidy_cost_usd == Decimal("0.400000")

    corrupt_request = Request.objects.get(pk=request_ids["corrupt-request"])
    assert corrupt_request.status == "operator_repair_required"
    assert corrupt_request.operator_repair_metadata["reason"] == (
        "legacy_negative_accounting_values"
    )
    assert corrupt_request.operator_repair_metadata["legacy_values"] == {
        "reserved_subsidy_usd": "-0.010000",
        "provider_cost_usd": "-0.020000",
        "subsidy_cost_usd": "-0.030000",
    }
    assert corrupt_request.reserved_subsidy_usd == 0
    assert corrupt_request.provider_cost_usd == 0
    assert corrupt_request.subsidy_cost_usd == 0

    corrupt_spend = Spend.objects.get(pk=spend_ids["anthropic"])
    assert corrupt_spend.requires_operator_repair is True
    assert corrupt_spend.operator_repair_metadata["legacy_values"] == {
        "reserved_subsidy_usd": "-0.100000",
        "provider_cost_usd": "-0.200000",
        "subsidy_cost_usd": "-0.300000",
    }
    assert corrupt_spend.reserved_subsidy_usd == 0
    assert corrupt_spend.provider_cost_usd == 0
    assert corrupt_spend.subsidy_cost_usd == 0


@pytest.mark.django_db(transaction=True)
def test_populated_migration_refuses_reverse_that_would_erase_audit_history(
    populated_funded_chat_0006,
):
    from django.db.migrations.exceptions import IrreversibleError

    # The fixture proves an empty schema can move back to 0006 for setup. Once
    # populated rows have been quarantined, rollback must fail closed.
    with pytest.raises(IrreversibleError, match="funded accounting rows present"):
        MigrationExecutor(connection).migrate(MIGRATE_FROM)
