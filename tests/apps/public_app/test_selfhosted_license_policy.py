"""The current self-hosted offer is AGPL or Enterprise by consultation."""

from datetime import date

import pytest
from django.template import Context, Engine
from django.utils.translation import override

from apps.infra.public_app import pricing, pricing_pages

TODAY = date(2026, 11, 16)


def _rows():
    return {row["id"]: row for row in pricing.published_price_rows(TODAY)}


def test_selfhosted_catalogue_has_two_license_choices():
    rows = _rows()
    assert {key for key in rows if key.startswith("selfhosted-")} == {
        "selfhosted-agpl", "selfhosted-commercial"
    }


def test_enterprise_is_quoted_without_a_numeric_floor():
    row = _rows()["selfhosted-commercial"]
    assert (row["price"], row["usd_amount"], row["is_from_price"]) == (
        "On request", None, False
    )


def test_cloud_academic_price_is_preserved():
    assert _rows()["subscription-student"]["price"] == "$19/mo"


def test_comparison_uses_the_same_enterprise_quote():
    rows = pricing.plan_comparison(TODAY)["rows"]
    price = next(row for row in rows if row.get("code") == "price")
    assert price["cells"][-1] == "On request"


def test_quote_has_no_invented_yen_reference():
    row = _rows()["selfhosted-commercial"]
    assert pricing.annotate_jpy_reference([row], 150)[0]["price_jpy"] == "—"


@pytest.mark.parametrize("language,expected", [("en", "On request"), ("ja", "要相談")])
def test_enterprise_quote_uses_the_active_language(language, expected):
    with override(language):
        assert _rows()["selfhosted-commercial"]["price"] == expected


@pytest.mark.parametrize("language,expected", [
    ("en", "AGPL-3.0 is available to anyone under its terms."),
    ("ja", "AGPL-3.0 は、その条件に従ってどなたでも利用できます。"),
])
def test_shared_policy_partial_renders_current_terms(language, expected):
    with override(language):
        template = Engine.get_default().get_template(
            "public_app/pricing_partials/policies.html"
        )
        html = template.render(Context(pricing_pages.pricing_page_context()))
    assert expected in html


def test_policy_partial_does_not_advertise_a_selfhosted_academic_license():
    template = Engine.get_default().get_template("public_app/pricing_partials/policies.html")
    html = template.render(Context(pricing_pages.pricing_page_context()))
    assert "Academic License" not in html


@pytest.mark.parametrize("item", [
    {"amount": None},
    {"amount": 0, "price_status": "on-request"},
    {"amount": None, "price_status": "unknown"},
    {"amount": None, "price_status": "on-request", "from_price": True},
    {"amount": None, "price_status": "on-request", "unit": "unknown"},
])
def test_invalid_price_records_fail_loudly(item):
    with pytest.raises((TypeError, ValueError)):
        pricing._published_price(item)


def test_explicit_quote_record_has_no_numeric_price():
    assert pricing._published_price({"amount": None, "price_status": "on-request"}) == "On request"


@pytest.mark.parametrize("language", ["en", "ja"])
@pytest.mark.parametrize("page", ["pages/pricing.html", "pages/services.html",
                                  "legal/tokushoho.html", "legal/tokushoho_en.html"])
def test_public_content_renders_without_retired_selfhosted_offers(page, language):
    # Render the actual content block without requiring the host's global shell.
    from django.template.loader_tags import BlockNode

    with override(language):
        template = Engine.get_default().get_template("public_app/" + page)
        context = Context({**pricing_pages.pricing_page_context(),
                           "published_price_rows": pricing.published_price_rows(TODAY)})
        content = next(node for node in template.nodelist.get_nodes_by_type(BlockNode)
                       if node.name == "content")
        with context.bind_template(template):
            html = content.render(context)
    assert not any(retired in html for retired in (
        "Self-Hosted — Academic License", "Academic License boundary", "$2,400",
        "セルフホスト — アカデミックライセンス",
    ))


@pytest.mark.parametrize("language,expected", [("en", "On request"), ("ja", "要相談")])
@pytest.mark.parametrize("page", ["pages/pricing.html", "pages/services.html",
                                  "legal/tokushoho.html", "legal/tokushoho_en.html"])
def test_public_content_displays_the_enterprise_quote(page, language, expected):
    from django.template.loader_tags import BlockNode

    with override(language):
        template = Engine.get_default().get_template("public_app/" + page)
        context = Context({**pricing_pages.pricing_page_context(),
                           "published_price_rows": pricing.published_price_rows(TODAY)})
        content = next(node for node in template.nodelist.get_nodes_by_type(BlockNode)
                       if node.name == "content")
        with context.bind_template(template):
            html = content.render(context)
    assert expected in html
