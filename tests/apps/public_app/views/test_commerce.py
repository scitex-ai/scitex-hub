#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the commerce/compliance pages (feat/tokushoho-stripe-pages).

Covers:
- 特定商取引法に基づく表記 (/tokushoho/): configured fields render;
  missing fields render an explicit 準備中 notice (no fake data);
  footer link present.
- Pricing page: honest 準備中 empty state; config-driven plans are
  staff-only while billing is in testing and display 税込 prices.
- Stripe scaffold: checkout/webhook return explicit 503 while
  unconfigured; webhook rejects bad signatures and records events for
  valid ones. Signature checks hand-roll Stripe's documented
  ``t=...,v1=HMAC_SHA256(secret, f"{t}.{payload}")`` scheme with a test
  secret — no mocks (STX-NM001).
"""

import hashlib
import hmac
import json
import time

import pytest
from django.urls import reverse

TEST_WEBHOOK_SECRET = (
    "whsec_test_secret_for_signature_checks"  # pragma: allowlist secret
)

TEST_PLANS = [
    {
        "name": "Pro (Test)",
        "price_tax_included": 1100,
        "currency": "jpy",
        "interval": "month",
        "stripe_price_id": "price_test_pro_monthly",
    }
]

CONFIGURED_COMPANY = {
    "COMPANY_NAME": "株式会社 SciTeX",
    "COMPANY_REPRESENTATIVE": "渡邉 裕亮",
    "COMPANY_ADDRESS": "静岡市葵区伝馬町1-2 テストビル301号室",
    "COMPANY_PHONE": "050-0000-0000",
    "COMPANY_CONTACT_EMAIL": "legal@scitex.ai",
}


def _stripe_signature(payload: bytes, secret: str, timestamp: int = None) -> str:
    """Hand-rolled Stripe-Signature header (documented v1 scheme)."""
    ts = int(time.time()) if timestamp is None else timestamp
    signed_payload = f"{ts}.".encode() + payload
    mac = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={mac}"


def _post_webhook(client, payload: bytes, signature: str = None):
    kwargs = {
        "data": payload,
        "content_type": "application/json",
    }
    if signature is not None:
        kwargs["HTTP_STRIPE_SIGNATURE"] = signature
    return client.post(reverse("public_app:stripe_webhook"), **kwargs)


@pytest.fixture
def staff_client(client, django_user_model):
    django_user_model.objects.create_user(
        username="operator-staff",
        password="test-password-123",
        is_staff=True,
    )
    client.login(username="operator-staff", password="test-password-123")
    return client


@pytest.fixture
def regular_client(client, django_user_model):
    django_user_model.objects.create_user(
        username="regular-user",
        password="test-password-123",
    )
    client.login(username="regular-user", password="test-password-123")
    return client


@pytest.mark.django_db
class TestTokushohoPage:
    """特定商取引法に基づく表記 page."""

    def test_tokushoho_page_returns_http_200(self, client):
        # Arrange
        url = reverse("public_app:tokushoho")
        # Act
        response = client.get(url)
        # Assert
        assert response.status_code == 200

    def test_tokushoho_page_shows_legal_heading(self, client):
        # Arrange
        url = reverse("public_app:tokushoho")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert "特定商取引法に基づく表記" in content

    @pytest.mark.parametrize("expected", list(CONFIGURED_COMPANY.values()))
    def test_tokushoho_with_configured_fields_renders_each_value(
        self, client, settings, expected
    ):
        # Arrange
        for key, value in CONFIGURED_COMPANY.items():
            setattr(settings, key, value)
        # Act
        content = client.get(reverse("public_app:tokushoho")).content.decode("utf-8")
        # Assert
        assert expected in content

    def test_tokushoho_missing_fields_render_pending_notices(self, client, settings):
        # Arrange: address / phone / email are NOT finalized
        settings.COMPANY_ADDRESS = ""
        settings.COMPANY_PHONE = ""
        settings.COMPANY_CONTACT_EMAIL = ""
        # Act
        content = client.get(reverse("public_app:tokushoho")).content.decode("utf-8")
        # Assert: one 準備中 notice per missing field, never a fake value
        assert content.count("tokushoho-pending") >= 3

    def test_tokushoho_without_plans_states_paid_plans_preparing(
        self, client, settings
    ):
        # Arrange
        settings.BILLING_PLANS = []
        # Act
        content = client.get(reverse("public_app:tokushoho")).content.decode("utf-8")
        # Assert
        assert "有料プランは現在準備中です" in content

    @pytest.mark.parametrize("expected", ["Pro (Test)", "1100", "税込"])
    def test_tokushoho_with_plans_lists_tax_inclusive_price_details(
        self, client, settings, expected
    ):
        # Arrange
        settings.BILLING_PLANS = TEST_PLANS
        # Act
        content = client.get(reverse("public_app:tokushoho")).content.decode("utf-8")
        # Assert
        assert expected in content

    def test_tokushoho_includes_no_refund_after_delivery_clause(self, client):
        # Arrange: 返品・キャンセル特約 (grant business/legal draft)
        url = reverse("public_app:tokushoho")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert (
            "提供開始後のお客様都合による返品・返金はお受けいたしません" in content
        )

    def test_tokushoho_includes_operating_environment_row(self, client):
        # Arrange
        url = reverse("public_app:tokushoho")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert "動作環境" in content

    def test_terms_page_footer_links_to_tokushoho(self, client):
        # Arrange: footer is global — a lightweight legal page carries it
        url = reverse("public_app:terms")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert reverse("public_app:tokushoho") in content


@pytest.mark.django_db
class TestPricingPage:
    """Pricing page — alpha-free framing + config-driven paid plans."""

    def test_pricing_without_plans_shows_preparing_notice(self, client, settings):
        # Arrange
        settings.BILLING_PLANS = []
        # Act
        content = client.get(reverse("public_app:pricing")).content.decode("utf-8")
        # Assert
        assert "有料プランは準備中です" in content

    def test_pricing_without_plans_links_to_contact_page(self, client, settings):
        # Arrange
        settings.BILLING_PLANS = []
        # Act
        content = client.get(reverse("public_app:pricing")).content.decode("utf-8")
        # Assert
        assert reverse("public_app:contact") in content

    def test_pricing_without_plans_has_no_checkout_form(self, client, settings):
        # Arrange
        settings.BILLING_PLANS = []
        # Act
        content = client.get(reverse("public_app:pricing")).content.decode("utf-8")
        # Assert
        assert reverse("public_app:billing_checkout") not in content

    def test_pricing_with_plans_hides_plan_names_from_anonymous(
        self, client, settings
    ):
        # Arrange: staff-only while billing is testing (operator directive)
        settings.BILLING_PLANS = TEST_PLANS
        # Act
        content = client.get(reverse("public_app:pricing")).content.decode("utf-8")
        # Assert
        assert "Pro (Test)" not in content

    @pytest.mark.parametrize("expected", ["Pro (Test)", "1100", "税込"])
    def test_pricing_with_plans_shows_tax_inclusive_details_to_staff(
        self, staff_client, settings, expected
    ):
        # Arrange
        settings.BILLING_PLANS = TEST_PLANS
        # Act
        content = staff_client.get(reverse("public_app:pricing")).content.decode(
            "utf-8"
        )
        # Assert
        assert expected in content

    def test_pricing_staff_without_stripe_keys_sees_disabled_note(
        self, staff_client, settings
    ):
        # Arrange
        settings.BILLING_PLANS = TEST_PLANS
        settings.STRIPE_SECRET_KEY = ""
        # Act
        content = staff_client.get(reverse("public_app:pricing")).content.decode(
            "utf-8"
        )
        # Assert
        assert "checkout disabled" in content


@pytest.mark.django_db
class TestBillingCheckout:
    """Checkout scaffold — staff-only, fail-loud when unconfigured."""

    def test_checkout_post_by_anonymous_returns_403(self, client):
        # Arrange
        url = reverse("public_app:billing_checkout")
        # Act
        response = client.post(url, {"price_id": "price_x"})
        # Assert
        assert response.status_code == 403

    def test_checkout_post_by_non_staff_returns_403(self, regular_client):
        # Arrange
        url = reverse("public_app:billing_checkout")
        # Act
        response = regular_client.post(url, {"price_id": "price_x"})
        # Assert
        assert response.status_code == 403

    def test_checkout_get_by_staff_returns_405(self, staff_client):
        # Arrange
        url = reverse("public_app:billing_checkout")
        # Act
        response = staff_client.get(url)
        # Assert
        assert response.status_code == 405

    def test_checkout_without_stripe_key_returns_503(self, staff_client, settings):
        # Arrange
        settings.STRIPE_SECRET_KEY = ""
        settings.BILLING_PLANS = TEST_PLANS
        # Act
        response = staff_client.post(
            reverse("public_app:billing_checkout"),
            {"price_id": "price_test_pro_monthly"},
        )
        # Assert
        assert response.status_code == 503

    def test_checkout_without_stripe_key_explains_missing_env_key(
        self, staff_client, settings
    ):
        # Arrange
        settings.STRIPE_SECRET_KEY = ""
        settings.BILLING_PLANS = TEST_PLANS
        # Act
        response = staff_client.post(
            reverse("public_app:billing_checkout"),
            {"price_id": "price_test_pro_monthly"},
        )
        # Assert
        assert "SCITEX_HUB_STRIPE_SECRET_KEY" in response.json()["detail"]

    def test_checkout_without_configured_plans_returns_503(
        self, staff_client, settings
    ):
        # Arrange
        settings.STRIPE_SECRET_KEY = "sk_test_placeholder"
        settings.BILLING_PLANS = []
        # Act
        response = staff_client.post(
            reverse("public_app:billing_checkout"), {"price_id": "price_x"}
        )
        # Assert
        assert response.status_code == 503

    def test_checkout_with_unknown_price_id_returns_400(self, staff_client, settings):
        # Arrange
        settings.STRIPE_SECRET_KEY = "sk_test_placeholder"
        settings.BILLING_PLANS = TEST_PLANS
        # Act
        response = staff_client.post(
            reverse("public_app:billing_checkout"),
            {"price_id": "price_not_configured"},
        )
        # Assert
        assert response.status_code == 400


@pytest.mark.django_db
class TestStripeWebhook:
    """Webhook — CSRF-exempt but signature-verified; records events."""

    def test_webhook_without_secret_returns_503(self, client, settings):
        # Arrange
        settings.STRIPE_WEBHOOK_SECRET = ""
        payload = json.dumps({"id": "evt_1", "type": "ping"}).encode()
        # Act
        response = _post_webhook(client, payload, "t=1,v1=deadbeef")
        # Assert
        assert response.status_code == 503

    def test_webhook_without_secret_explains_missing_env_key(self, client, settings):
        # Arrange
        settings.STRIPE_WEBHOOK_SECRET = ""
        payload = json.dumps({"id": "evt_1", "type": "ping"}).encode()
        # Act
        response = _post_webhook(client, payload, "t=1,v1=deadbeef")
        # Assert
        assert "SCITEX_HUB_STRIPE_WEBHOOK_SECRET" in response.json()["detail"]

    def test_webhook_without_signature_header_returns_400(self, client, settings):
        # Arrange
        settings.STRIPE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
        payload = json.dumps({"id": "evt_2", "type": "ping"}).encode()
        # Act
        response = _post_webhook(client, payload, signature=None)
        # Assert
        assert response.status_code == 400

    def test_webhook_with_wrong_secret_signature_returns_400(self, client, settings):
        # Arrange
        settings.STRIPE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
        payload = json.dumps({"id": "evt_3", "type": "ping"}).encode()
        signature = _stripe_signature(payload, "whsec_wrong_secret")
        # Act
        response = _post_webhook(client, payload, signature)
        # Assert
        assert response.status_code == 400

    def test_webhook_with_tampered_payload_returns_400(self, client, settings):
        # Arrange: signature is valid for the ORIGINAL payload only
        settings.STRIPE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
        original = json.dumps({"id": "evt_4", "type": "ping"}).encode()
        signature = _stripe_signature(original, TEST_WEBHOOK_SECRET)
        tampered = json.dumps({"id": "evt_4", "type": "hacked"}).encode()
        # Act
        response = _post_webhook(client, tampered, signature)
        # Assert
        assert response.status_code == 400

    def test_webhook_with_stale_timestamp_returns_400(self, client, settings):
        # Arrange: valid HMAC but timestamp outside the replay tolerance
        settings.STRIPE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
        payload = json.dumps({"id": "evt_5", "type": "ping"}).encode()
        stale = int(time.time()) - 3600
        signature = _stripe_signature(payload, TEST_WEBHOOK_SECRET, timestamp=stale)
        # Act
        response = _post_webhook(client, payload, signature)
        # Assert
        assert response.status_code == 400

    def test_webhook_with_valid_signature_returns_200(self, client, settings):
        # Arrange
        settings.STRIPE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
        payload = json.dumps({"id": "evt_ok_1", "type": "ping"}).encode()
        signature = _stripe_signature(payload, TEST_WEBHOOK_SECRET)
        # Act
        response = _post_webhook(client, payload, signature)
        # Assert
        assert response.status_code == 200

    def test_webhook_with_valid_signature_creates_billing_event_row(
        self, client, settings
    ):
        # Arrange
        from apps.infra.public_app.models import BillingEvent

        settings.STRIPE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
        payload = json.dumps(
            {"id": "evt_ok_2", "type": "checkout.session.completed"}
        ).encode()
        signature = _stripe_signature(payload, TEST_WEBHOOK_SECRET)
        # Act
        _post_webhook(client, payload, signature)
        # Assert
        assert BillingEvent.objects.filter(event_id="evt_ok_2").exists()

    def test_webhook_stores_event_type_from_payload(self, client, settings):
        # Arrange
        from apps.infra.public_app.models import BillingEvent

        settings.STRIPE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
        payload = json.dumps(
            {"id": "evt_ok_3", "type": "checkout.session.completed"}
        ).encode()
        signature = _stripe_signature(payload, TEST_WEBHOOK_SECRET)
        # Act
        _post_webhook(client, payload, signature)
        # Assert
        assert (
            BillingEvent.objects.get(event_id="evt_ok_3").event_type
            == "checkout.session.completed"
        )

    def test_webhook_duplicate_event_reports_created_false(self, client, settings):
        # Arrange: deliver the same event twice (Stripe retries)
        settings.STRIPE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
        payload = json.dumps({"id": "evt_dup_1", "type": "ping"}).encode()
        signature = _stripe_signature(payload, TEST_WEBHOOK_SECRET)
        _post_webhook(client, payload, signature)
        # Act
        second = _post_webhook(client, payload, signature)
        # Assert
        assert second.json()["created"] is False

    def test_webhook_duplicate_event_keeps_single_row(self, client, settings):
        # Arrange
        from apps.infra.public_app.models import BillingEvent

        settings.STRIPE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
        payload = json.dumps({"id": "evt_dup_2", "type": "ping"}).encode()
        signature = _stripe_signature(payload, TEST_WEBHOOK_SECRET)
        _post_webhook(client, payload, signature)
        # Act
        _post_webhook(client, payload, signature)
        # Assert
        assert BillingEvent.objects.filter(event_id="evt_dup_2").count() == 1

    def test_webhook_with_non_json_body_returns_400(self, client, settings):
        # Arrange: correctly signed but not JSON
        settings.STRIPE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
        payload = b"not-json"
        signature = _stripe_signature(payload, TEST_WEBHOOK_SECRET)
        # Act
        response = _post_webhook(client, payload, signature)
        # Assert
        assert response.status_code == 400


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
