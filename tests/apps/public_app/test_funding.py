#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the /funding/ route and /.well-known/funding.json manifest.

Constraints:
- /funding/ renders the plan from data/funding.json (the operator's
  funding manifest) via funding.funding_plan() — never a literal amount
  in the template.
- /.well-known/funding.json serves the manifest verbatim.
- The plan badge shows $25,000 USD/yearly from plan.amount_display,
  plan.currency and plan.frequency.
"""

import json
import os
import re
from pathlib import Path

import pytest

PUBLIC_APP = Path(__file__).resolve().parents[3] / "apps" / "infra" / "public_app"
_PRICE_LITERAL = re.compile(r"(?:[$¥]\s?\d[\d,]*)|(?:\d[\d,]*\s?円)")

# Same probe as tests/apps/public_app/views/test_pages.py: Django-dependent
# tests skip (not error) where the full stack is unavailable.
DJANGO_AVAILABLE = False
try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.settings_dev")
    import django

    django.setup()
    DJANGO_AVAILABLE = True
except Exception:
    pass

requires_django = pytest.mark.skipif(not DJANGO_AVAILABLE, reason="Django not available")


class TestFundingManifestData:
    def test_manifest_exists_and_parses(self):
        from apps.infra.public_app.funding import FUNDING_PATH, load_funding

        assert FUNDING_PATH.exists()
        assert load_funding()["version"] == "v1.1.0"

    def test_manifest_steward_is_scitex_inc(self):
        from apps.infra.public_app.funding import load_funding

        assert load_funding()["entity"]["name"] == "SciTeX Inc."

    @requires_django
    def test_plan_amount_display_currency_frequency(self):
        from apps.infra.public_app.funding import funding_plan

        plan = funding_plan()
        assert plan["amount"] == 25000
        assert plan["amount_display"] == "$25,000"
        assert plan["currency"] == "USD"
        assert plan["frequency"] == "yearly"


class TestFormatFundingAmount:
    def test_whole_dollars(self):
        from apps.infra.public_app.funding import format_funding_amount

        assert format_funding_amount(25000) == "$25,000"

    def test_zero(self):
        from apps.infra.public_app.funding import format_funding_amount

        assert format_funding_amount(0) == "$0"


class TestFundingTemplateGuard:
    def test_fundraising_template_has_no_price_literal(self):
        template = (
            PUBLIC_APP / "templates" / "public_app" / "pages" / "fundraising.html"
        )
        assert template.exists()
        assert _PRICE_LITERAL.search(template.read_text(encoding="utf-8")) is None


@requires_django
@pytest.mark.django_db
class TestFundingRoutes:
    def test_funding_url_reverses(self):
        from django.urls import reverse

        assert reverse("public_app:funding") == "/funding/"

    def test_manifest_url_reverses(self):
        from django.urls import reverse

        assert reverse("public_app:funding_manifest") == "/.well-known/funding.json"

    def test_funding_page_returns_200(self, client):
        assert client.get("/funding/").status_code == 200

    def test_funding_page_shows_plan_badge(self, client):
        content = client.get("/funding/").content.decode()
        assert "$25,000" in content
        assert "USD" in content
        assert "yearly" in content

    def test_funding_page_links_manifest(self, client):
        content = client.get("/funding/").content.decode()
        assert "/.well-known/funding.json" in content

    def test_manifest_serves_verbatim(self, client):
        from apps.infra.public_app.funding import FUNDING_PATH

        response = client.get("/.well-known/funding.json")
        assert response.status_code == 200
        served = json.loads(response.content.decode())
        assert served == json.loads(FUNDING_PATH.read_text(encoding="utf-8"))

    def test_manifest_plan_is_25k_yearly(self, client):
        served = json.loads(client.get("/.well-known/funding.json").content.decode())
        plan = served["funding"]["plans"][0]
        assert plan["amount"] == 25000
        assert plan["currency"] == "USD"
        assert plan["frequency"] == "yearly"


@requires_django
@pytest.mark.django_db
class TestFundingEntrySurface:
    def test_signup_page_links_funding(self, client):
        from django.urls import reverse

        content = client.get(reverse("auth_app:signup")).content.decode()
        assert "/funding/" in content
