#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the /services page (services list + inquiry form).

Covers the load-bearing constraints from the design spec:
- The page renders in Japanese with the services + transparency sections.
- Every inquiry is PERSISTED (ServiceInquiry) so no lead is lost.
- Required-field validation stores nothing on error.
- Email is sent ONLY when SERVICES_INQUIRY_EMAIL is set, and NEVER to recruit@.
"""

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
