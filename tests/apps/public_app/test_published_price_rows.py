"""published_price_rows(): the date gate closes, opens on the month, and every
unit in the catalogue is one the formatter knows.

The gate test carries its own positive control in BOTH directions — the same
row hidden before its month and shown from its month — because a gate that is
only ever observed closed is indistinguishable from a filter that drops
everything.
"""

from datetime import date, timedelta

from apps.infra.public_app.pricing import (
    format_amount,
    load_pricing,
    published_price_rows,
)


def _catalogue():
    return load_pricing()["published_prices"]


def test_a_future_dated_row_is_hidden_and_then_shown_from_its_month() -> None:
    # Arrange
    gated = [r for r in _catalogue() if r.get("available_from")]
    assert gated, (
        "Control: the catalogue has no available_from row, so this test cannot "
        "observe the gate. Add one, or delete this test deliberately."
    )
    row = gated[0]
    year, month = (int(x) for x in row["available_from"].split("-"))
    on_the_month = date(year, month, 1)
    before = on_the_month - timedelta(days=1)  # last day of the previous month

    # Act
    ids_before = {r["id"] for r in published_price_rows(today=before)}
    ids_on = {r["id"] for r in published_price_rows(today=on_the_month)}

    # Assert
    assert row["id"] not in ids_before, (
        f"{row['id']} is dated {row['available_from']} but rendered on {before}."
    )
    assert row["id"] in ids_on, (
        f"{row['id']} is dated {row['available_from']} and did NOT render on "
        f"{on_the_month} — the gate never opens, which is a filter, not a gate."
    )


def test_rows_without_a_date_are_always_published() -> None:
    # Arrange
    undated = {r["id"] for r in _catalogue() if not r.get("available_from")}
    assert undated, "Control: every catalogue row is date-gated; nothing to assert."

    # Act
    ids = {r["id"] for r in published_price_rows(today=date(2000, 1, 1))}

    # Assert
    assert undated <= ids


def test_every_catalogue_unit_is_one_the_formatter_renders() -> None:
    """format_amount raises on an unknown unit — by design, so a bare number
    never ships without its 月額 / 1件 / 1時間 prefix. The date gate skips
    future rows before formatting, so this walks the catalogue directly."""
    for row in _catalogue():
        rendered = format_amount(row["amount"], row.get("unit", "once"))
        assert rendered.endswith("円"), (row["id"], rendered)
