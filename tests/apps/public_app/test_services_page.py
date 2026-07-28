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
