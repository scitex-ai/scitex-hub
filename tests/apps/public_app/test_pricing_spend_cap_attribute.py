"""``spend_cap`` in pricing.json: validated, read by spend controls, never stated.

The per-plan cap values are provisional (mirrored from the scitex-affairs
catalog) and spend controls start in shadow mode, so the price pages must keep
saying only that the cap is user-set, while a malformed cap fails CI.
"""

import json
from pathlib import Path

import pytest

from apps.infra.public_app.pricing import (
    PRICING_PATH,
    displayed_attributes,
    included_items,
    published_price_rows,
)


def _capped_rows() -> list[dict]:
    rows = json.loads(Path(PRICING_PATH).read_text(encoding="utf-8"))[
        "published_prices"
    ]
    return [r for r in rows if "spend_cap" in r.get("attributes", {})]


def test_every_subscription_row_carries_a_spend_cap() -> None:
    # Arrange
    rows = json.loads(Path(PRICING_PATH).read_text(encoding="utf-8"))[
        "published_prices"
    ]
    # Act
    uncapped = [
        r["id"]
        for r in rows
        if r.get("category") == "subscription"
        and "spend_cap" not in r.get("attributes", {})
    ]
    # Assert
    assert uncapped == []


def test_spend_cap_is_not_a_displayed_attribute() -> None:
    # Arrange
    rows = _capped_rows()
    # Act
    leaked = [
        r["id"] for r in rows if "spend_cap" in displayed_attributes(r["attributes"])
    ]
    # Assert
    assert rows and leaked == []


def test_spend_cap_adds_no_phrase_to_what_a_plan_includes() -> None:
    # Arrange
    attributes = {
        "overage": "metered",
        "spend_cap": {"default_usd": 20, "max_usd": 500, "unit": "USD/billing-cycle"},
    }
    # Act
    items = included_items(attributes)
    # Assert
    assert items == included_items({"overage": "metered"})


def test_published_rows_never_state_a_cap_maximum() -> None:
    # Arrange
    maxima = {r["id"]: r["attributes"]["spend_cap"]["max_usd"] for r in _capped_rows()}
    # Act
    stated = [
        (row["id"], item)
        for row in published_price_rows()
        if maxima.get(row["id"])
        for item in row["included"] + row["remarks"]
        if f"${maxima[row['id']]}" in item
    ]
    # Assert
    assert stated == []


@pytest.mark.parametrize(
    "bad",
    [
        {"default_usd": 10},
        {"default_usd": 30, "max_usd": 20},
        {"default_usd": -1, "max_usd": 20},
        {"default_usd": "10", "max_usd": 20},
        {"default_usd": True, "max_usd": 20},
        {"default_usd": 10, "max_usd": 20, "unit": "JPY/month"},
        {"default_usd": 10, "max_usd": 20, "hard_limit": True},
        [10, 20],
    ],
)
def test_a_malformed_spend_cap_fails_loudly(bad) -> None:
    # Arrange
    attributes = {"spend_cap": bad}
    # Act
    render = lambda: included_items(attributes)  # noqa: E731
    # Assert
    with pytest.raises(ValueError):
        render()
