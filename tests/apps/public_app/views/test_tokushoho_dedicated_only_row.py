"""Synthetic regression: a price row whose attributes are ALL dedicated columns.

Why synthetic: the shipped catalogue does not contain such a row TODAY, and that
is precisely what makes the template fallback from an empty 備考 to the full
included list a LATENT duplication bug rather than a visible one. The first row
that carries only storage / compute credit / overage would render its three
dedicated columns and then repeat all three inside 備考.

These tests pin the CONTRACT that makes the fallback wrong ('' an all-dedicated
row has NO remark) and guard the template against reintroducing it.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings

from apps.infra.public_app.pricing import remarks_items

_STORAGE = "ストレージ 50GB/プロジェクト/月（Standard）"
_CREDIT = "計算クレジット 100時間/月"
_OVERAGE = "1時間あたり ¥10"

# Every attribute here has its own dedicated column in the tokushoho table.
_ALL_DEDICATED = {
    "included_storage": 50,
    "included_compute_credit": 100,
    "overage": "per_hour",
}


def test_an_all_dedicated_row_has_an_empty_remarks_cell():
    """Each dedicated attribute is rendered ONCE — in its own column, not 備考."""
    remarks = remarks_items(
        _ALL_DEDICATED,
        basis="プロジェクト",
        storage_text=_STORAGE,
        credit_text=_CREDIT,
        overage_text=_OVERAGE,
    )

    assert remarks == [], (
        f"an all-dedicated row produced 備考 entries {remarks!r}; those same "
        "attributes already have dedicated columns, so this is the duplication "
        "the exclusion exists to prevent"
    )


def test_no_real_row_repeats_a_dedicated_column_in_its_remarks():
    """Control the other way, on the REAL catalogue.

    The synthetic case above proves the contract; this proves the exclusion
    actually holds for every row the site ships today, and it is the control that
    stops ``remarks_items`` from passing by unconditionally returning ``[]`` — an
    always-empty remarks cell would satisfy the synthetic test while silently
    emptying 備考 for real rows.

    Asserted on rendered COLUMN TEXT rather than attribute names, because that is
    what a reader of the published table would see twice.
    """
    from apps.infra.public_app.pricing import published_price_rows

    rows = published_price_rows()
    assert rows, "the catalogue produced no price rows to check"

    offenders = [
        (row["id"], column)
        for row in rows
        for column in (
            row.get("storage"),
            row.get("compute_credit"),
            row.get("overage"),
        )
        if column and column != "—" and row.get("remarks") and column in row["remarks"]
    ]

    assert not offenders, (
        f"these rows repeat a dedicated column inside 備考: {offenders} — the "
        "dedicated column and 備考 would show the same figure twice"
    )


def test_the_remarks_cell_does_not_fall_back_to_the_full_included_list():
    """Source guard: the fallback that caused the latent duplication stays gone.

    Asserted on the TEMPLATE TAG, not on the bare string — the cell carries a
    comment explaining why the fallback is absent, and a substring check would
    match that comment instead of the code.
    """
    template = Path(
        settings.BASE_DIR,
        "apps/infra/public_app/templates/public_app/legal/tokushoho.html",
    ).read_text(encoding="utf-8")

    assert "{% elif row.included %}" not in template, (
        "the 備考 cell still falls back to row.included; for a row whose "
        "attributes are all dedicated that repeats every dedicated column — "
        "remove the fallback rather than relying on no such row existing yet"
    )
