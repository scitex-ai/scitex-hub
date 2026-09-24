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
    assert "Cool ストレージ 2 GB 込み" in free_included


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


def test_self_hosted_license_group_contrasts_agpl_vs_commercial() -> None:
    """The Non-AGPL incentives (commercial use, support, SLA) render from
    BOTH self-hosted rows' SSOT license_terms — never typed in the template.
    """
    from apps.infra.public_app.pricing import plan_comparison

    rows = plan_comparison()["rows"]
    by_label = {r["label"]: r["cells"] for r in rows if "label" in r}
    assert by_label["Commercial use"] == [
        "—",
        "—",
        "Source disclosure required",
        "No restrictions",
    ]
    assert by_label["Support"] == ["—", "—", "Community", "Included"]
    assert by_label["SLA"] == ["—", "—", "—", "Included"]


def test_metered_rates_and_api_rows_come_from_the_ssot() -> None:
    """CPU/RAM/GPU rates, API keys and API services render from rate_card —
    the table can never disagree with the pricing page's rate list.
    """
    from apps.infra.public_app.pricing import plan_comparison

    rows = plan_comparison()["rows"]
    by_label = {r["label"]: r["cells"] for r in rows if "label" in r}
    assert by_label["Metered CPU"][0] == "$0.05 / CPU Unit-hour"
    assert by_label["Metered CPU"][2] == "—"  # self-hosted runs on your hardware
    assert by_label["Metered memory"][0] == "$0.005 / GiB-hour"
    # One row per GPU class (a combined cell became an unreadable tower
    # on narrow displays); VRAM lives in the class names, not its own row.
    assert by_label["RTX 4090 class"][0] == "$0.70 / GPU-hour"
    assert by_label["A100 80 GB class"][0] == "$2.00 / GPU-hour"
    assert by_label["B200 class"][0] == "$7.00 / GPU-hour"
    assert "VRAM" not in by_label
    # The included-GPU row is separate from the metered per-class rows.
    assert by_label["GPU"][0] == "No GPU"
    # Only short price rows opt into mobile nowrap; sentence cells wrap.
    nowrap = {
        r["label"]: r.get("nowrap", False) for r in rows if "label" in r
    }
    assert nowrap["Metered CPU"] is True
    assert nowrap["RTX 4090 class"] is True
    assert nowrap["API keys"] is True
    assert nowrap["Scholar, Stats, FigRecipe and Writer"] is False
    assert nowrap["Compute credits"] is False
    assert by_label["API keys"] == ["Rate-limited", "Included", "—", "—"]
    services = by_label["Scholar, Stats, FigRecipe and Writer"]
    assert "no separate per-app fee" in services[0]
    assert "20% service fee" not in services[0]
    assert "(Coming soon)" in services[0]
    assert services[2] == "—"
    groups = [r["group"] for r in rows if "group" in r]
    assert "Metered compute rates (Coming soon)" in groups
    assert "Applications" in groups
    agents = by_label["Agents"]
    assert "model API × 110%" in agents[0]
    assert agents[2] == "—"
    model_api = by_label["Model API"]
    assert "depends on the service" in model_api[0]


@translation.override("ja")
def test_license_and_notes_render_japanese() -> None:
    """New compare-table strings must not silently fall back to English."""
    from apps.infra.public_app.pricing import plan_comparison

    comp = plan_comparison()
    rows = comp["rows"]
    by_label = {r["label"]: r["cells"] for r in rows if "label" in r}
    comm_use = next(r["cells"] for r in rows if "cells" in r and r["cells"][2:] == ["ソース開示が必要", "制限なし"])
    assert comm_use[:2] == ["—", "—"]
    assert by_label["CPU"][2] == "ご自身のハードウェア"
    notes = " ".join(comp["notes"])
    assert "VRAMの単独料金はありません" in notes
    assert "コンピュートクレジットは、" in notes


@translation.override("ja")
def test_metered_and_api_rows_render_japanese() -> None:
    from apps.infra.public_app.pricing import plan_comparison

    rows = plan_comparison()["rows"]
    cells = [str(c) for r in rows if "cells" in r for c in r["cells"]]
    text = " ".join(cells)
    assert "CPUユニット時間" in text
    assert "レート制限あり" in text
    assert "通常のコンピュート" in text


def test_table_notes_come_from_the_ssot() -> None:
    """Footnotes stay minimal: credit value, VRAM bundling, speed honesty.

    Tier meanings and speeds live under the tier names in the row labels,
    the academic discount lives in the Pro price cell — the bottom of the
    table keeps only what fits no cell. Self-hosted resource cells stay a
    short line, not a repeated paragraph.
    """
    from apps.infra.public_app.pricing import plan_comparison

    comp = plan_comparison()
    notes = comp["notes"]
    assert any("$1" in n and "Compute Credit" in n for n in notes)
    assert any("no separate VRAM rate" in n for n in notes)
    assert any("approximate live measurements" in n for n in notes)
    assert not any("storage:" in n for n in notes)
    rows = comp["rows"]
    by_label = {r["label"]: r["cells"] for r in rows if "label" in r}
    assert by_label["CPU"][2] == "Your own hardware"
    cool_key = next(k for k in by_label if k.startswith("Cool"))
    assert by_label[cool_key][2] == "Your own hardware"
    assert not any(
        "Runs on your own hardware" in c
        for r in rows if "cells" in r for c in r["cells"]
    )
    price_row = next(r for r in rows if r.get("label") == "Price")
    assert "academic (50% off)" in price_row["cells"][1]
    coupon_row = next(r for r in rows if r.get("label") == "Coupons")
    assert coupon_row["cells"] == [
        "—",
        "Coupon codes accepted (Coming soon)",
        "—",
        "On request",
    ]
    hot_key = next(k for k in by_label if k.startswith("Hot"))
    assert "tier-speed" in hot_key and "tier-sub" in hot_key
    cols = comp["columns"]
    assert [c["label"] for c in cols] == [
        "SciTeX™ Cloud Free",
        "SciTeX™ Cloud Pro",
        "SciTeX™ Self-Hosted (AGPL)",
        "SciTeX™ Self-Hosted (Enterprise)",
    ]
    assert [c["recommended"] for c in cols] == [False, True, False, False]
    assert all(c["cta_label"] and c["cta_url"] for c in cols)
    assert cols[2]["cta_external"] is True
    assert comp["coupon_codes"] == [
        {
            "code": "ACADEMIC50",
            "description": "Academic — 50% off Pro",
            "price": "$19/mo",
        }
    ]
