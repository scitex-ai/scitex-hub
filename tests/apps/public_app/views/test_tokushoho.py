#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the 特定商取引法に基づく表記 page (/tokushoho/).

Split out of test_commerce.py (512-line file limit); the Stripe /
pricing / checkout tests stay there.

Covers:
- Configured fields render; missing fields render an explicit 準備中
  notice (no fake data); footer link present.
- Committed config defaults (config/settings/settings_commerce.py):
  registered address 〒420-0857 静岡県静岡市葵区御幸町３－２１ペガサートビル７階静岡市コ・クリエーションスペース内 and
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
    # Not a COMPANY_* key, but it must be popped for the same reason: without
    # it, a default-value assertion would read whatever the ambient
    # environment happens to set and pass for the wrong reason.
    "SCITEX_HUB_SERVICES_INQUIRY_EMAIL",
    "SCITEX_CLOUD_SERVICES_INQUIRY_EMAIL",
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
        # (no room number; 〒420-0857 from the 国税庁 registry, 2026-08-28)
        url = reverse("public_app:tokushoho")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert "〒420-0857 静岡県静岡市葵区御幸町３－２１ペガサートビル７階静岡市コ・クリエーションスペース内" in content

    def test_tokushoho_default_renders_representative_phone(self, client):
        # Arrange: no overrides — the committed config default applies
        # (operator-confirmed 2026-07-18)
        url = reverse("public_app:tokushoho")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert "080-4022-3567" in content

    def test_tokushoho_without_billing_plans_publishes_the_price_list(
        self, client, settings
    ):
        """No Stripe plan configured is the PRODUCTION state, and the page must
        still say what the paid tiers cost.

        This branch used to render 有料プランは現在準備中です. That was true while
        no price had been decided; it stopped being true on 2026-08-28, when the
        prices were published and only the PAYMENT path stayed pending. A 特商法
        page that hides the price of the thing it is selling is exactly the
        defect this branch exists to prevent — so the assertion MOVED to the new
        requirement rather than being deleted.

        Prices are read from ``subscription_rows()``, the same pricing.json
        source the page renders, so this test cannot drift into a hardcoded
        number that silently contradicts the page.
        """
        # Arrange
        from apps.infra.public_app.pricing import subscription_rows

        settings.BILLING_PLANS = []
        rows = subscription_rows()
        assert rows, (
            "Control: subscription_rows() returned nothing, so every price "
            "assertion below would pass vacuously. pricing.json lost its "
            "subscription amounts — fix that, do not weaken this test."
        )

        # Act
        content = client.get(reverse("public_app:tokushoho")).content.decode("utf-8")

        # Assert
        for row in rows:
            assert row["price"] in content, (
                f"pricing.json prices {row['name']} at {row['price']}, but the "
                "特商法 page does not show it."
            )
        assert "審査完了後に開始" in content, (
            "The page must state that online card payment opens after the "
            "Stripe review — that is the only part still 準備中."
        )

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
        # Assert: registered address — registered office; 〒420-0857
        # operator-confirmed 2026-07-17 (grant, 日本郵便 lookup)
        assert module.COMPANY_ADDRESS == "〒420-0857 静岡県静岡市葵区御幸町３－２１ペガサートビル７階静岡市コ・クリエーションスペース内"

    def test_company_phone_defaults_to_representative_number(
        self, commerce_settings_clean_env
    ):
        # Arrange: company env keys are unset (fixture)
        module = commerce_settings_clean_env
        # Act
        module = importlib.reload(module)
        # Assert: operator-confirmed representative number (2026-07-18)
        assert module.COMPANY_PHONE == "080-4022-3567"

    def test_company_contact_email_defaults_to_confirmed_address(
        self, commerce_settings_clean_env
    ):
        # Arrange: company env keys are unset (fixture)
        module = commerce_settings_clean_env
        # Act
        module = importlib.reload(module)
        # Assert: operator-confirmed public contact (2026-07-30). This test
        # previously asserted "" — the address was genuinely undecided, and the
        # empty value rendered 準備中 rather than a guess. It is decided now, so
        # the assertion moves with the decision instead of being deleted: a
        # 特商法 contact is a statutory declaration, and an empty one shipping
        # unnoticed is the failure this pins against.
        assert module.COMPANY_CONTACT_EMAIL == "info@scitex.ai"

    def test_services_inquiry_email_defaults_to_confirmed_address(
        self, commerce_settings_clean_env
    ):
        """A /services lead must reach a human, not just a DB row.

        Operator-confirmed 2026-07-30. This one is pinned because it is a
        BEHAVIOUR switch, not a displayed string: empty means every inquiry is
        persisted and nobody is notified, so a regression to "" would silently
        stop lead notifications while the form kept reporting success and the
        rows kept accumulating. Nothing would look broken.
        """
        # Arrange: company/services env keys are unset (fixture)
        module = commerce_settings_clean_env

        # Act
        module = importlib.reload(module)

        # Assert
        assert module.SERVICES_INQUIRY_EMAIL == "info@scitex.ai", (
            "SERVICES_INQUIRY_EMAIL drives whether /services inquiries are "
            "emailed at all. Empty = persisted but nobody notified. If the "
            "operator changed the destination, update this literal in the "
            "same commit."
        )

    def test_branding_does_not_define_the_legal_contact(self):
        """The legal contact must not become an alias of the general contact.

        ``branding.CONTACT_EMAIL`` holds the same string as
        ``COMPANY_CONTACT_EMAIL`` today, so a refactor that "deduplicated" them
        would look correct and keep every other test here green. They are the
        same value and not the same fact: this one is a 特定商取引法 declaration
        that may only change by operator decision, the other is a product
        choice. Keeping the legal contact out of branding is what stops a future
        contact-address sweep from rewriting a statutory filing.
        """
        # Arrange
        from config import branding

        # Act
        branding_names = dir(branding)

        # Assert
        assert "COMPANY_CONTACT_EMAIL" not in branding_names, (
            "config.branding must not define COMPANY_CONTACT_EMAIL — the legal "
            "contact lives in config/settings/settings_commerce.py so a "
            "contact-address refactor cannot silently change a legal filing."
        )


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
