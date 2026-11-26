"""What the price catalog says about an account: its plan, cap bounds, rates.

The catalog is ``public_app/data/pricing.json``, the Hub's copy of the
scitex-affairs catalog (USD is the source of truth; the affairs repo's
``scripts/pricing/check_drift.py`` keeps the two equal). The Hub never imports
scitex-affairs.

Each subscription row carries::

    "spend_cap": {"default_usd": 10, "max_usd": 200, "unit": "USD/billing-cycle"}

``default_usd`` is the conservative cap a new account starts with;
``max_usd`` is the most the holder may raise it to without contacting us.
A row without ``spend_cap`` RAISES: an account whose plan does not state its
limits must not silently run uncapped.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

FREE_PLAN_ID = "subscription-free"


class CatalogError(RuntimeError):
    """The catalog is missing something spend controls cannot guess."""


@dataclass(frozen=True)
class PlanTerms:
    pricing_id: str
    label: str
    default_cap_usd: Decimal
    max_cap_usd: Decimal
    included_storage_gb: Decimal
    storage_tier: str
    included_compute_credit_usd: Decimal
    included_egress_gb: Decimal
    workspace_cpus: int
    workspace_memory_gb: int


@dataclass(frozen=True)
class Rates:
    cpu_unit_hour_usd: Decimal
    memory_addon_gib_hour_usd: Decimal
    storage_gb_month_usd: dict
    egress_gb_usd: Decimal
    gib_per_cpu_unit: int = 4


def _pricing():
    from apps.infra.public_app.pricing import load_pricing

    return load_pricing()


def _dec(value, default="0") -> Decimal:
    if value is None:
        value = default
    return Decimal(str(value))


def _row(pricing_id: str) -> dict:
    for row in _pricing()["published_prices"]:
        if row.get("id") == pricing_id and row.get("category") == "subscription":
            return row
    raise CatalogError(f"pricing.json has no subscription row {pricing_id!r}")


def plan_terms(pricing_id: str) -> PlanTerms:
    row = _row(pricing_id)
    attrs = row.get("attributes", {}) or {}
    cap = attrs.get("spend_cap")
    if not cap or "default_usd" not in cap or "max_usd" not in cap:
        raise CatalogError(
            f"pricing.json row {pricing_id!r} has no spend_cap.default_usd/max_usd. "
            "Add them in the scitex-affairs catalog and mirror them here; an "
            "account must never run without a stated cap."
        )
    default_cap = _dec(cap["default_usd"])
    max_cap = _dec(cap["max_usd"])
    if default_cap < 0 or max_cap < default_cap:
        raise CatalogError(
            f"pricing.json row {pricing_id!r}: need 0 <= default_usd <= max_usd"
        )
    storage = attrs.get("included_storage", {}) or {}
    credit = attrs.get("included_compute_credit", {}) or {}
    egress = attrs.get("included_egress", {}) or {}
    limits = attrs.get("workspace_limits", {}) or {}
    return PlanTerms(
        pricing_id=pricing_id,
        label=row.get("label", pricing_id),
        default_cap_usd=default_cap,
        max_cap_usd=max_cap,
        included_storage_gb=_dec(storage.get("amount")),
        storage_tier=storage.get("tier", "Cool"),
        # A credit marked coming_soon is not granted yet: counting it would
        # quietly raise everyone's effective cap by its amount.
        included_compute_credit_usd=(
            Decimal("0") if credit.get("coming_soon") else _dec(credit.get("amount"))
        ),
        included_egress_gb=_dec(egress.get("amount")),
        workspace_cpus=int(limits.get("cpu", 1) or 1),
        workspace_memory_gb=int(limits.get("memory_gb", 2) or 2),
    )


def rates() -> Rates:
    card = _pricing()["rate_card"]
    tiers = {t["name"]: _dec(t.get("amount")) for t in card["storage_tiers"]}
    return Rates(
        cpu_unit_hour_usd=_dec(card["compute"]["cpu_unit_rate"]),
        memory_addon_gib_hour_usd=_dec(card["compute"]["memory_addon_rate"]),
        storage_gb_month_usd=tiers,
        egress_gb_usd=_dec(card["network"]["egress_over_amount"]),
    )


def plan_id_for(user) -> str:
    """The plan the account is on: provider-confirmed subscription, else the
    plan the onboarding authority recorded at activation, else Free."""
    from apps.infra.public_app.models import PlanSubscription

    sub = (
        PlanSubscription.objects.filter(
            user=user, status__in=PlanSubscription.CURRENT_STATUSES
        )
        .order_by("-created_at")
        .first()
    )
    if sub is not None and sub.pricing_id:
        return sub.pricing_id
    # Only an ACTIVATED authority counts: the plan picked on the payment step
    # is recorded before the provider confirms anything.
    state = getattr(user, "onboarding_state", None)
    recorded = (
        state.pricing_id
        if state is not None and state.step == state.Step.PRODUCT
        else ""
    )
    if recorded:
        # A PAID plan is only real while a current subscription backs it (the
        # branch above). A recorded $0 plan needs no provider and is honoured.
        try:
            if _dec(_row(recorded).get("amount")) <= 0:
                return recorded
        except CatalogError:
            pass
    return FREE_PLAN_ID


__all__ = [
    "CatalogError",
    "FREE_PLAN_ID",
    "PlanTerms",
    "Rates",
    "plan_id_for",
    "plan_terms",
    "rates",
]
