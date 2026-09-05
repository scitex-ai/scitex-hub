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
    # A withheld row never publishes, so it cannot serve as the control for a
    # gate that must be seen OPEN as well as closed.
    gated = [
        r for r in _catalogue()
        if r.get("available_from") and not str(r.get("withheld", "")).strip()
    ]
    assert gated, (
        "Control: no un-withheld row carries available_from, so this test cannot "
        "observe the gate opening. Add one, or delete this test deliberately."
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


def test_a_withheld_row_is_not_published_whatever_its_date_says() -> None:
    """withheld is a GATE with a stated reason; a blank reason is not a hold."""
    from unittest import mock
    from apps.infra.public_app import pricing

    fake = {"published_prices": [
        {"id": "held", "label": "A", "amount": 100, "unit": "month", "available_from": "2000-01",
         "withheld": "list price under an active discount; presentation undecided"},
        {"id": "blank", "label": "B", "amount": 100, "unit": "month", "available_from": "2000-01",
         "withheld": "   "},
        {"id": "open", "label": "C", "amount": 100, "unit": "month", "available_from": "2000-01"},
    ]}
    with mock.patch.object(pricing, "load_pricing", return_value=fake):
        ids = {r["id"] for r in pricing.published_price_rows(today=date(2026, 9, 2))}
    assert ids == {"blank", "open"}, ids


def test_no_catalogue_row_is_withheld_today() -> None:
    """Pins the 2026-09-02 20:09Z ruling (business, case A): the two
    subscription rows publish at the early-adopter price. The previous
    version of this test pinned the opposite — the withheld field and that
    test were deleted in the same commit, as its docstring required."""
    held = {r["id"] for r in _catalogue() if str(r.get("withheld", "")).strip()}
    assert held == set(), held


def test_the_subscription_rows_sell_at_the_launch_price_until_july_2027() -> None:
    """The real catalogue, on days either side of the Launch/Y1 window's end.
    1,490 / 2,990 are 2,980 / 5,980 at 50%; the note carries business's final
    form (2026-09-03 06:54Z; operator Telegram 6913/6915): list price and
    discount first, then the period, then every later stage and finally the
    list price from the day after the last window. Windows are selected BY
    DATE, so on 2027-08-01 the Y2 (30%) window applies without anyone editing
    a status flag; after Y3 ends (2029-08-01) the list price returns with no
    note. Both directions, so a renderer that ignored the calendar fails on
    one side and one that never stopped discounting on the other."""
    by_id = {r["id"]: r for r in published_price_rows(today=date(2026, 9, 2))}
    assert by_id["subscription-student"]["label"] == "サブスク・学術"
    assert by_id["subscription-student"]["price"] == "月額 1,490円"
    assert by_id["subscription-general"]["price"] == "月額 2,990円"
    assert by_id["subscription-student"]["price_note"] == (
        "定価 2,980円、早期導入割引 50%。2027年7月末までの早期導入価格。"
        "2027年8月から 2,086円、2028年8月から 2,682円、2029年8月から 2,980円"
    ), by_id["subscription-student"]["price_note"]
    assert by_id["subscription-general"]["price_note"] == (
        "定価 5,980円、早期導入割引 50%。2027年7月末までの早期導入価格。"
        "2027年8月から 4,186円、2028年8月から 5,382円、2029年8月から 5,980円"
    ), by_id["subscription-general"]["price_note"]

    by_id = {r["id"]: r for r in published_price_rows(today=date(2027, 8, 1))}
    assert by_id["subscription-student"]["price"] == "月額 2,086円"
    assert by_id["subscription-general"]["price"] == "月額 4,186円"
    assert by_id["subscription-student"]["price_note"] == (
        "定価 2,980円、早期導入割引 30%。2028年7月末までの早期導入価格。"
        "2028年8月から 2,682円、2029年8月から 2,980円"
    ), by_id["subscription-student"]["price_note"]

    by_id = {r["id"]: r for r in published_price_rows(today=date(2029, 8, 1))}
    assert by_id["subscription-student"]["price"] == "月額 2,980円"
    assert by_id["subscription-general"]["price"] == "月額 5,980円"
    assert by_id["subscription-student"]["price_note"] == ""
    assert by_id["subscription-general"]["price_note"] == ""


def _policy_fixture(schedule, amount=1000):
    return {
        "pricing_policies": {"p": {"schedule": schedule}},
        "published_prices": [
            {"id": "row", "label": "A", "amount": amount, "unit": "month",
             "available_from": "2000-01", "policy": "p"},
        ],
    }


def test_a_window_is_selected_by_date_whatever_its_status_says() -> None:
    """Rule check independent of the data file. business.yaml's `status` marks
    which single phase is current and may not be set on two at once; the
    engine (Price.from_mapping) selects the phase whose dates cover the day,
    and so does this renderer (business, 2026-09-03 06:54Z). A window marked
    `proposed` that covers today therefore DOES discount — the 50→30→10 taper
    is a settled decision, not a plan — and a day no window covers sells at
    the list price with no note."""
    from unittest import mock
    from apps.infra.public_app import pricing

    fake = _policy_fixture([
        {"label": "x", "start": "2026-01-01", "end": "2026-12-31", "percent": 50, "status": "proposed"},
    ])
    with mock.patch.object(pricing, "load_pricing", return_value=fake):
        (inside,) = pricing.published_price_rows(today=date(2026, 9, 2))
        (outside,) = pricing.published_price_rows(today=date(2027, 1, 1))
    assert inside["price"] == "月額 500円", inside
    assert inside["price_note"] == "定価 1,000円、早期導入割引 50%。2026年12月末までの早期導入価格。2027年1月から 1,000円", inside
    assert outside["price"] == "月額 1,000円" and outside["price_note"] == "", outside


def test_the_note_names_a_mid_month_end_and_every_later_stage() -> None:
    """A mid-month end is named by the day (月末 is only for a last-of-month
    end), a mid-month start likewise; the later windows are listed in date
    order at their own percent; the list price follows the LAST window."""
    from unittest import mock
    from apps.infra.public_app import pricing

    chained = _policy_fixture([
        {"label": "a", "start": "2026-01-01", "end": "2026-12-15", "percent": 50, "status": "active"},
        {"label": "b", "start": "2026-12-16", "end": "2027-12-31", "percent": 20, "status": "proposed"},
    ])
    with mock.patch.object(pricing, "load_pricing", return_value=chained):
        (row,) = pricing.published_price_rows(today=date(2026, 9, 2))
    assert row["price"] == "月額 500円", row
    assert row["price_note"] == (
        "定価 1,000円、早期導入割引 50%。2026年12月15日までの早期導入価格。"
        "2026年12月16日から 800円、2028年1月から 1,000円"
    ), row


def test_a_fractional_yen_discount_is_refused() -> None:
    from unittest import mock

    import pytest

    from apps.infra.public_app import pricing

    fake = _policy_fixture([
        {"label": "x", "start": "2000-01-01", "end": "2999-12-31", "percent": 50, "status": "active"},
    ], amount=999)
    with mock.patch.object(pricing, "load_pricing", return_value=fake):
        with pytest.raises(ValueError, match="whole yen"):
            pricing.published_price_rows(today=date(2026, 9, 2))


def test_a_row_citing_an_undefined_policy_is_refused() -> None:
    from unittest import mock

    import pytest

    from apps.infra.public_app import pricing

    fake = _policy_fixture([])
    fake["pricing_policies"] = {}
    with mock.patch.object(pricing, "load_pricing", return_value=fake):
        with pytest.raises(ValueError, match="pricing_policies"):
            pricing.published_price_rows(today=date(2026, 9, 2))


def test_every_catalogue_attribute_renders_as_one_phrase() -> None:
    """The 特商法 page states サービスの内容 from each row's attributes. An
    attribute name or value the renderer does not know raises here — at CI,
    when the catalogue is committed — rather than on the legal page."""
    from apps.infra.public_app.pricing import included_items

    seen = 0
    for row in _catalogue():
        attributes = row.get("attributes", {})
        items = included_items(attributes)
        assert len(items) == len(attributes), (row["id"], items)
        assert all(item.strip() for item in items), (row["id"], items)
        seen += len(items)
    assert seen, "Control: no row carries attributes, so nothing was rendered."


def test_the_subscription_rows_state_what_they_include() -> None:
    """Pins the upstream numbers the operator confirmed 2026-09-02 (50 GB,
    1,000円 compute credit, metered overage, user-set cap) so a copy of
    business.yaml that dropped one fails here."""
    by_id = {r["id"]: r for r in published_price_rows(today=date(2026, 9, 2))}
    for row_id in ("subscription-student", "subscription-general"):
        text = "、".join(by_id[row_id]["included"])
        for needle in ("ストレージ 50GB/月", "計算クレジット 1,000円相当/月", "超過分は従量課金", "月の上限は利用者が設定"):
            assert needle in text, (row_id, text)
    assert "対象: 大学・研究機関のメールアドレスを持つこと（学生・院生・教職員・研究員）" in "、".join(by_id["subscription-student"]["included"])
    assert "対象: " not in "、".join(by_id["subscription-general"]["included"])


def test_overlapping_windows_are_refused() -> None:
    """Two windows covering the same day is an upstream data error; the page
    must not silently pick one (the first in file order would win)."""
    from unittest import mock

    import pytest

    from apps.infra.public_app import pricing

    fake = _policy_fixture([
        {"label": "a", "start": "2026-01-01", "end": "2026-12-31", "percent": 50, "status": "active"},
        {"label": "b", "start": "2026-06-01", "end": "2027-12-31", "percent": 30, "status": "proposed"},
    ])
    with mock.patch.object(pricing, "load_pricing", return_value=fake):
        with pytest.raises(ValueError, match="must not overlap"):
            pricing.published_price_rows(today=date(2026, 9, 2))
