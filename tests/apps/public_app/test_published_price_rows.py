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


def test_every_hand_entered_row_carries_available_from() -> None:
    """The publication rule is business.yaml's: no available_from = not for
    sale at a list price = NOT on the page. That makes a forgotten date on a
    hand-entered row a silent omission at runtime — so it is caught HERE,
    at CI, where it is loud, rather than as a missing line on a legal page."""
    missing = [r["id"] for r in _catalogue() if not r.get("available_from")]
    assert not missing, (
        f"published_prices rows without available_from: {missing}. Every row "
        "in pricing.json is for sale at a list price and must say from when; "
        "upstream's usage-billed rows (no date) are not copied here at all."
    )


def test_a_row_with_no_date_is_not_published() -> None:
    """Rule check on the function itself, independent of the data file."""
    from unittest import mock
    from apps.infra.public_app import pricing

    fake = {"published_prices": [
        {"id": "dated", "label": "A", "amount": 100, "unit": "month", "available_from": "2000-01"},
        {"id": "undated", "label": "B", "amount": 100, "unit": "month"},
    ]}
    with mock.patch.object(pricing, "load_pricing", return_value=fake):
        ids = {r["id"] for r in pricing.published_price_rows(today=date(2026, 9, 2))}
    assert ids == {"dated"}, ids


def test_every_catalogue_unit_is_one_the_formatter_renders() -> None:
    """format_amount raises on an unknown unit — by design, so a bare number
    never ships without its 月額 / 1件 / 1時間 prefix. The date gate skips
    future rows before formatting, so this walks the catalogue directly."""
    for row in _catalogue():
        rendered = format_amount(row["amount"], row.get("unit", "once"))
        assert rendered.endswith("円"), (row["id"], rendered)
