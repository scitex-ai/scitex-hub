"""published_price_rows(): the date gate closes, opens on the month, and every
unit in the catalogue is one the formatter knows.

The gate test carries its own positive control in BOTH directions — the same
row hidden before its month and shown from its month — because a gate that is
only ever observed closed is indistinguishable from a filter that drops
everything.
"""

from datetime import date, timedelta
import subprocess
import sys
from pathlib import Path

import pytest

from django.utils import translation

from apps.infra.public_app.pricing import (
    format_amount,
    load_pricing,
    published_price_rows,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module", autouse=True)
def compiled_catalogs():
    """Compile locale/**/*.po -> .mo before any JA assertion reads a catalog.

    The SSoT is now English-sourced (2026-09-11); the tests below pin the
    JAPANESE catalog renderings, so the .mo must exist and Django's per-language
    translation cache must be clear (same fixture the i18n landing tests use).
    """
    script = PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    result = subprocess.run(
        [sys.executable, str(script)], cwd=PROJECT_ROOT,
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"catalog compilation failed ({result.returncode}):\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    translation.trans_real._translations.clear()
    yield

# The SSoT is now ENGLISH-sourced (2026-09-11: landing/pricing English by
# default, JA only after selection). The exact rendered strings below are the
# JAPANESE catalog translations, so pin them under translation.override("ja")
# — that keeps every assertion meaningful (it still verifies the JA wording)
# while the English default is covered by the landing i18n tests.


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
        # A bare number must never ship: the rendered string carries more than
        # the raw figure (a unit prefix in EN, or the currency suffix in JA).
        assert rendered.strip() != f"{row['amount']:,}", (row["id"], rendered)
        # A free row (the AGPL / Academic self-hosted licenses) renders "Free".
        assert row["amount"] == 0 or any(ch.isdigit() for ch in rendered), (row["id"], rendered)


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


@translation.override("ja")
def test_the_subscription_rows_show_flat_usd() -> None:
    """SSOT Provisional v1.0 (2026-09-14): Cloud Academic $19/mo and Cloud
    Standard $39/mo, flat, whatever the calendar date. The early-adopter
    discount schedule and the stored JPY list amounts were removed with it."""
    # Arrange
    days = (date(2026, 9, 2), date(2027, 8, 1), date(2029, 8, 1))
    # Act
    prices = [
        tuple(r["price"] for r in published_price_rows(today=d) if r["category"] == "subscription")
        for d in days
    ]
    # Assert
    assert prices == [("無料", "$19/mo", "$39/mo")] * len(days)


@translation.override("ja")
def test_the_academic_cloud_label_translates_to_japanese() -> None:
    # Arrange
    from apps.infra.public_app.templatetags.landing_i18n import translate_dynamic

    by_id = {r["id"]: r for r in published_price_rows(today=date(2026, 9, 2))}
    # Act
    label = translate_dynamic(by_id["subscription-student"]["label"])
    # Assert
    assert label == "SciTeX Cloud Pro - Academic（学術）"


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


@translation.override("ja")
def test_the_subscription_rows_state_what_they_include() -> None:
    """Pins SSOT v1.0 §2 (32 GB Cool, $10 credit — coming soon, 100 GB egress,
    30-day trial, metered overage, user-set cap — coming soon)."""
    # Arrange
    needles = (
        "30日間の無料トライアル",
        "Cool ストレージ 32 GB 込み",
        "計算クレジット $10 / 請求サイクル（近日提供）",
        "インターネットへの送信 100 GB",
        "含まれる量を超えたストレージと送信は従量課金",
        "月間の利用上限を利用者が設定（近日提供）",
    )
    # Act: the paid rows carry the full §2 list; the Free row is exempt —
    # it has no trial, no 32 GB, no metered overage — but must say no card.
    missing = [
        (row["id"], needle)
        for row in published_price_rows(today=date(2026, 9, 2))
        if row["category"] == "subscription" and row["id"] != "subscription-free"
        for needle in needles
        if needle not in "、".join(row["included"])
    ]
    free_included = "、".join(
        item
        for row in published_price_rows(today=date(2026, 9, 2))
        if row["id"] == "subscription-free"
        for item in row["included"]
    )
    # Assert
    assert missing == []
    assert "クレジットカードの登録は不要" in free_included


@translation.override("ja")
def test_only_the_academic_cloud_row_states_an_eligibility_rule() -> None:
    # Arrange
    rows = published_price_rows(today=date(2026, 9, 2))
    # Act
    eligible = [r["id"] for r in rows if any(i.startswith("対象: ") for i in r["included"])]
    # Assert
    assert eligible == ["subscription-student"]


@translation.override("ja")
def test_percent_notes_render_japanese_not_english_fallback() -> None:
    """Django's {% trans %} looks literals up DOUBLED (value.replace("%","%%")).

    A single-% msgid in django.po therefore misses SILENTLY and the page shows
    English (measured live 2026-08-23 for "100% open-source", and again for
    these two notes). The repo convention: template keeps single %, .po msgid
    carries %%, msgstr single %. This test renders the tag the way the
    template does, so a reverted msgid fails HERE instead of on the live page.
    """
    from django.template import Context, Template

    cases = {
        "Academic users get Pro at 50% off with a university email address.":
            "50%オフ",
        "Pay-as-you-go (PAYG) usage beyond your plan is billed at provider "
        "cost plus a 20% service fee.":
            "20%のサービス料",
    }
    for literal, ja_needle in cases.items():
        rendered = Template('{% load i18n %}{% trans "' + literal + '" %}').render(
            Context()
        )
        assert ja_needle in rendered, (
            f"{{% trans {literal!r} %}} rendered English under ja: {rendered!r}. "
            "The django.po msgid must carry %% (doubled percent)."
        )
