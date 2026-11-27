"""The account-wide billing rules the catalog states (operator decisions
2026-11-27, a-h), read through ``catalog.billing_policy()``.

The decisions themselves are mirrored from the scitex-affairs catalog; these
tests pin that the Hub reads them, refuses an inconsistent copy, and that the
storage meter honours "backups are not counted" (decision b).
"""

import copy
from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def pricing():
    from apps.infra.public_app.pricing import load_pricing

    return copy.deepcopy(load_pricing())


@pytest.mark.parametrize(
    "field, expected",
    [
        ("currency_of_record", "USD"),  # h
        ("overseas_customers_accepted", True),  # h
        ("jp_tax_inclusive_display", True),  # g
        ("payers", frozenset({"individual", "organization"})),  # a
        ("storage_counts_backups", False),  # b
        ("ingress_free", True),  # d
        ("public_download_paid_by", "scitex"),  # c
        ("public_download_monthly_cap_gb", None),  # c: cap not decided
        ("api_calls_billed", False),
        ("credit_sources", ("plan_grant", "prepaid_topup")),
        ("external_services_markup_percent", Decimal("20")),  # f
    ],
)
def test_the_catalog_states_the_decided_billing_policy(field, expected):
    # Arrange
    from apps.infra.spend_app.services import catalog

    # Act
    policy = catalog.billing_policy()
    # Assert
    assert getattr(policy, field) == expected


@pytest.mark.parametrize("plan", ["subscription-student", "subscription-general"])
def test_paid_plans_include_32_gb_storage_and_100_gb_egress(plan):  # e
    # Arrange
    from apps.infra.spend_app.services import catalog

    # Act
    terms = catalog.plan_terms(plan)
    # Assert
    assert (terms.included_storage_gb, terms.included_egress_gb) == (
        Decimal("32"),
        Decimal("100"),
    )


def test_a_catalog_without_a_billing_policy_raises(pricing):
    # Arrange
    from apps.infra.spend_app.services import catalog

    del pricing["billing_policy"]
    # Act
    call = lambda: catalog.billing_policy(pricing)  # noqa: E731
    # Assert
    with pytest.raises(catalog.CatalogError, match="no billing_policy"):
        call()


@pytest.mark.parametrize(
    "path",
    [
        ("rate_card", "payg_margin_pct"),
        ("rate_card", "compute", "external_fee_percent"),
        ("rate_card", "api", "agents_fee_percent"),
    ],
)
def test_an_external_service_markup_that_differs_from_the_flat_rate_raises(
    pricing, path
):  # f
    # Arrange
    from apps.infra.spend_app.services import catalog

    node = pricing
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = 10
    # Act
    call = lambda: catalog.billing_policy(pricing)  # noqa: E731
    # Assert
    with pytest.raises(catalog.CatalogError, match="one flat markup"):
        call()


def test_an_unknown_payer_kind_raises(pricing):
    # Arrange
    from apps.infra.spend_app.services import catalog

    pricing["billing_policy"]["payers"] = ["individual", "sponsor"]
    # Act
    call = lambda: catalog.billing_policy(pricing)  # noqa: E731
    # Assert
    with pytest.raises(catalog.CatalogError, match="payers"):
        call()


def test_a_currency_of_record_other_than_the_catalog_currency_raises(
    pricing
):  # h
    # Arrange
    from apps.infra.spend_app.services import catalog

    pricing["billing_policy"]["currency_of_record"] = "JPY"
    # Act
    call = lambda: catalog.billing_policy(pricing)  # noqa: E731
    # Assert
    with pytest.raises(catalog.CatalogError, match="currency_of_record"):
        call()


def test_the_storage_meter_does_not_count_backup_snapshots(user, settings, tmp_path):
    """Decision b against the REAL scanner, not an injected byte count.

    ``scripts/deployment/backup_workspaces.sh`` writes snapshots to
    ``$BASE_DIR/backups/snapshots/<user>_<project>_<ts>/``. A full copy of the
    user's project there must add nothing to the user's storage.
    """
    # Arrange
    from apps.infra.spend_app.services import usage

    settings.BASE_DIR = tmp_path
    project = tmp_path / "data" / "users" / user.username / "proj" / "p1"
    project.mkdir(parents=True)
    (project / "data.bin").write_bytes(b"x" * 1_000)
    snapshot = tmp_path / "backups" / "snapshots" / f"{user.username}_p1_20261127"
    snapshot.mkdir(parents=True)
    (snapshot / "data.bin").write_bytes(b"x" * 1_000)
    # Act
    counted = usage._scan_storage_bytes(user)
    # Assert
    assert counted == 1_000


def test_a_catalog_that_counts_backups_stops_the_meter(
    user, subscription, pricing
):  # b
    # Arrange
    from apps.infra.spend_app.services import catalog, usage

    pricing["billing_policy"]["storage_counts_backups"] = True
    _, start, end = usage.period_bounds()
    source = usage.ProvisionalUsageSource(
        storage_bytes_fn=lambda u: 0,
        billing_policy_fn=lambda: catalog.billing_policy(pricing),
    )
    # Act
    call = lambda: source.snapshot(user, start=start, end=end)  # noqa: E731
    # Assert
    with pytest.raises(catalog.CatalogError, match="cannot count backups"):
        call()


def test_the_storage_line_tells_the_user_backups_are_not_counted(user, subscription):
    # Arrange
    from apps.infra.spend_app.services import usage

    _, start, end = usage.period_bounds()
    source = usage.ProvisionalUsageSource(storage_bytes_fn=lambda u: 0)
    # Act
    snap = source.snapshot(user, start=start, end=end)
    storage = next(l for l in snap.lines if l.resource == "storage")
    # Assert
    assert "backup copies are not counted" in storage.note
