#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the 特定商取引法に基づく表記 page (/tokushoho/).

Split out of test_commerce.py (512-line file limit); the Stripe /
pricing / checkout tests stay there.

Covers:
- Configured fields render; missing fields render an explicit 準備中
  notice (no fake data); footer link present.
- Committed config defaults (config/settings/settings_commerce.py):
  registered address 〒420-0839 静岡県静岡市葵区鷹匠2-8-10 and
  representative phone 080-4022-3567 (operator-confirmed 2026-07-18;
  〒 confirmed 2026-07-17 via grant); public contact email stays
  unset (準備中).
"""

import importlib
import os

import pytest
from django.urls import reverse

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

_COMPANY_ENV_KEYS = (
    "SCITEX_HUB_COMPANY_ADDRESS",
    "SCITEX_CLOUD_COMPANY_ADDRESS",
    "SCITEX_HUB_COMPANY_PHONE",
    "SCITEX_CLOUD_COMPANY_PHONE",
    "SCITEX_HUB_COMPANY_CONTACT_EMAIL",
    "SCITEX_CLOUD_COMPANY_CONTACT_EMAIL",
)


@pytest.fixture
def commerce_settings_clean_env():
    """settings_commerce module with company env keys unset (real env).

    Pops the SCITEX_{HUB,CLOUD}_COMPANY_* keys from ``os.environ`` so the
    committed code defaults apply, yields the module for the test to
    reload, then restores the environment and reloads the module so the
    interpreter-wide state matches the real environment again.
    """
    from config.settings import settings_commerce

    saved = {
        key: os.environ.pop(key)
        for key in _COMPANY_ENV_KEYS
        if key in os.environ
    }
    yield settings_commerce
    os.environ.update(saved)
    importlib.reload(settings_commerce)


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
        # Arrange: empty values (no-fake-data guard — an unset field must
        # render 準備中, never a fabricated value)
        settings.COMPANY_ADDRESS = ""
        settings.COMPANY_PHONE = ""
        settings.COMPANY_CONTACT_EMAIL = ""
        # Act
        content = client.get(reverse("public_app:tokushoho")).content.decode("utf-8")
        # Assert: one 準備中 notice per missing field, never a fake value
        assert content.count("tokushoho-pending") >= 3

    def test_tokushoho_default_renders_registered_address(self, client):
        # Arrange: no overrides — the committed config default applies
        # (no room number; 〒420-0839 operator-confirmed 2026-07-17)
        url = reverse("public_app:tokushoho")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert "〒420-0839 静岡県静岡市葵区鷹匠2-8-10" in content

    def test_tokushoho_default_renders_representative_phone(self, client):
        # Arrange: no overrides — the committed config default applies
        # (operator-confirmed 2026-07-18)
        url = reverse("public_app:tokushoho")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert "080-4022-3567" in content

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


class TestCommerceSettingsDefaults:
    """Committed defaults in config/settings/settings_commerce.py.

    Address and phone are operator-confirmed (2026-07-18) and ship as
    code defaults; the public contact email is still unconfirmed and
    MUST default to empty (準備中). Pure config contract — no DB.
    """

    def test_company_address_defaults_to_registered_address(
        self, commerce_settings_clean_env
    ):
        # Arrange: company env keys are unset (fixture)
        module = commerce_settings_clean_env
        # Act
        module = importlib.reload(module)
        # Assert: registered address — no room number; 〒420-0839
        # operator-confirmed 2026-07-17 (grant, 日本郵便 lookup)
        assert module.COMPANY_ADDRESS == "〒420-0839 静岡県静岡市葵区鷹匠2-8-10"

    def test_company_phone_defaults_to_representative_number(
        self, commerce_settings_clean_env
    ):
        # Arrange: company env keys are unset (fixture)
        module = commerce_settings_clean_env
        # Act
        module = importlib.reload(module)
        # Assert: operator-confirmed representative number (2026-07-18)
        assert module.COMPANY_PHONE == "080-4022-3567"

    def test_company_contact_email_defaults_to_empty(
        self, commerce_settings_clean_env
    ):
        # Arrange: company env keys are unset (fixture)
        module = commerce_settings_clean_env
        # Act
        module = importlib.reload(module)
        # Assert: still unconfirmed — stays 準備中 (no fake data)
        assert module.COMPANY_CONTACT_EMAIL == ""


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
