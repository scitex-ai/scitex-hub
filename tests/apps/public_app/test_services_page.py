#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the /services page (services list + inquiry form).

Covers the load-bearing constraints from the design spec:
- The page renders in Japanese with the services + transparency sections.
- Every inquiry is PERSISTED (ServiceInquiry) so no lead is lost.
- Required-field validation stores nothing on error.
- Email is sent ONLY when SERVICES_INQUIRY_EMAIL is set, and NEVER to recruit@.
"""

from pathlib import Path

import pytest
from django.core import mail
from django.urls import reverse

from apps.infra.public_app.models import ServiceInquiry


@pytest.fixture
def services_url():
    return reverse("public_app:services")


@pytest.fixture
def valid_payload():
    return {
        "name": "山田太郎",
        "affiliation": "〇〇大学 △△研究室",
        "request": "Python の解析代行をお願いしたいです。",
        "budget": "10万円くらい",
    }


@pytest.fixture
def posted_valid(client, services_url, valid_payload, settings):
    """POST a valid inquiry with NO inquiry email configured."""
    settings.SERVICES_INQUIRY_EMAIL = ""
    return client.post(services_url, valid_payload)


@pytest.fixture
def posted_with_email(client, services_url, valid_payload, settings):
    """POST a valid inquiry WITH an inquiry email configured (locmem backend)."""
    settings.SERVICES_INQUIRY_EMAIL = "inbox@example.com"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    return client.post(services_url, valid_payload)


@pytest.fixture
def posted_invalid(client, services_url):
    """POST with the required fields empty."""
    return client.post(services_url, {"name": "", "request": ""})


@pytest.mark.django_db
class TestServicesGet:
    def test_get_returns_200(self, client, services_url):
        # Arrange
        # Act
        resp = client.get(services_url)
        # Assert
        assert resp.status_code == 200

    def test_get_lists_a_service(self, client, services_url):
        # Arrange
        # Act
        resp = client.get(services_url)
        # Assert
        assert "解析相談・コードレビュー" in resp.content.decode()

    def test_get_shows_transparency_section(self, client, services_url):
        # Arrange
        # Act
        resp = client.get(services_url)
        # Assert: external usage fees are billed at cost (pricing transparency)
        assert "外部利用料" in resp.content.decode()

    def test_get_shows_pricing_ladder(self, client, services_url):
        # Arrange
        # Act
        resp = client.get(services_url)
        # Assert
        assert "料金の目安" in resp.content.decode()

    def test_get_offers_a_free_first_consult(self, client, services_url):
        # Arrange
        # Act
        resp = client.get(services_url)
        # Assert
        assert "無料" in resp.content.decode()

    def test_get_leads_with_no_lock_in_positioning(self, client, services_url):
        # Arrange
        # Act
        resp = client.get(services_url)
        # Assert
        assert "囲い込" in resp.content.decode()

    def test_get_prices_the_same_catalogue_as_tokushoho(self, client, services_url):
        """2026-09-02: /services/ and /tokushoho/ read ONE list. Until then this
        page rendered the 2024-invoice consulting bands and a three-tier table
        whose middle tier (Lab) business had retired on 2026-08-28 — two public
        pages, one pricing.json, two disjoint price sets. The operator's words
        on seeing it: 「値段はめちゃくちゃだった」."""
        # Arrange
        from apps.infra.public_app.pricing import published_price_rows

        rows = published_price_rows()
        assert rows, "Control: an empty catalogue would satisfy the loop below vacuously."
        # Act
        content = client.get(services_url).content.decode()
        # Assert — every published row, by label AND price, is on the page
        for row in rows:
            assert row["label"] in content and row["price"] in content, (
                f"{row['label']} {row['price']} is in pricing.json but not on /services/."
            )
        for row in rows:
            if row["price_note"]:
                assert row["price_note"] in content, f"{row['label']}: {row['price_note']!r} not on /services/"
            for item in row["included"]:
                assert item in content, f"{row['label']}: included item {item!r} not on /services/"
        assert "税込" in content

    def test_get_no_longer_prices_retired_offers(self, client, services_url):
        # Arrange
        retired_tier_names = ("Individual", "Enterprise")  # the old three-tier table
        retired_band_amounts = ("11,000", "33,000", "110,000")  # 2024-invoice bands
        # Act
        content = client.get(services_url).content.decode()
        # Assert
        for needle in retired_tier_names + retired_band_amounts:
            assert needle not in content, f"retired {needle!r} is back on /services/"
        # The grid container is class="svc-plan-cards" and shares the prefix;
        # count the tier articles, not every class that starts that way.
        assert content.count('<article class="svc-plan-card') == 3, "exactly three tiers"

    def test_get_shows_the_three_tiers_business_wrote(self, client, services_url):
        # Arrange
        expected = ("サブスク", "オンプレ", "大規模", "応相談", "問い合わせはこちら")
        # Act
        content = client.get(services_url).content.decode()
        # Assert
        for needle in expected:
            assert needle in content, f"{needle!r} missing from the tier cards"


@pytest.mark.django_db
class TestServicesInquiryValid:
    def test_valid_post_returns_200(self, posted_valid):
        # Arrange
        # Act
        # Assert
        assert posted_valid.status_code == 200

    def test_valid_post_shows_success(self, posted_valid):
        # Arrange
        # Act
        # Assert
        assert "受け付けました" in posted_valid.content.decode()

    def test_valid_post_persists_one_inquiry(self, posted_valid):
        # Arrange
        # Act
        # Assert
        assert ServiceInquiry.objects.count() == 1

    def test_valid_post_stores_name(self, posted_valid):
        # Arrange
        # Act
        # Assert
        assert ServiceInquiry.objects.get().name == "山田太郎"

    def test_valid_post_without_address_sends_no_email(self, posted_valid):
        # Arrange
        # Act
        # Assert
        assert len(mail.outbox) == 0


@pytest.mark.django_db
class TestServicesInquiryInvalid:
    def test_invalid_post_shows_error(self, posted_invalid):
        # Arrange
        # Act
        # Assert
        assert "ご記入ください" in posted_invalid.content.decode()

    def test_invalid_post_saves_nothing(self, posted_invalid):
        # Arrange
        # Act
        # Assert
        assert ServiceInquiry.objects.count() == 0


@pytest.mark.django_db
class TestServicesInquiryEmail:
    def test_configured_address_sends_one_email(self, posted_with_email):
        # Arrange
        # Act
        # Assert
        assert len(mail.outbox) == 1

    def test_email_goes_to_configured_address(self, posted_with_email):
        # Arrange
        # Act
        # Assert
        assert mail.outbox[0].to == ["inbox@example.com"]

    def test_email_never_goes_to_recruit(self, posted_with_email):
        # Arrange
        # Act
        # Assert
        assert not any("recruit@" in addr for addr in mail.outbox[0].to)


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])


_SERVICES_CSS = (
    Path(__file__).resolve().parents[3]
    / "apps/infra/public_app/static/public_app/css"
)


def _rules_for(selector: str, css: str) -> list[str]:
    """Every declaration block whose selector list contains ``selector`` exactly,
    at top level or inside any @media block."""
    import re

    # Comments first: a `/* … */` directly above a rule would otherwise be
    # captured as part of its selector list, and the rule this test exists
    # for (services.css's old `.svc-plan-cards { display: none }`) sat under
    # exactly such a comment — the first version of this parser missed it.
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    blocks = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selectors = [s.strip() for s in m.group(1).split(",")]
        if selector in selectors:
            blocks.append(m.group(2))
    return blocks


def test_the_tier_cards_are_not_hidden_by_any_stylesheet_the_page_loads():
    """Measured on production 2026-09-04: the three tier cards were in the HTML
    (the substring tests above were green) and rendered 0×0, because
    services.css still carried the old mobile-only `.svc-plan-cards {
    display: none }` from before #708 moved the tiers into these cards. A
    rendered-HTML test cannot see CSS, so this one reads the two stylesheets
    the page links and refuses any rule that hides the container — at top
    level OR inside a media query — while a positive control proves the
    parser sees the container's real rule."""
    import re

    hides = []
    seen = 0
    for name in ("services.css", "services-detail.css"):
        css = (_SERVICES_CSS / name).read_text(encoding="utf-8")
        for block in _rules_for(".svc-plan-cards", css):
            seen += 1
            if re.search(r"display\s*:\s*none", block) or re.search(r"visibility\s*:\s*hidden", block):
                hides.append((name, block.strip()))
    assert seen >= 1, "Control: no rule for .svc-plan-cards was parsed at all, so the assertion below is vacuous."
    assert not hides, f"the tier-card container is hidden by: {hides}"
