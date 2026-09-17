"""Landing page tells a customer story before naming implementation details."""

from __future__ import annotations

import re
from pathlib import Path

TEMPLATES = (
    Path(__file__).resolve().parents[3]
    / "apps"
    / "infra"
    / "public_app"
    / "templates"
    / "public_app"
    / "landing_partials"
)
HERO = (TEMPLATES / "landing_hero.html").read_text(encoding="utf-8")
MODULES = (TEMPLATES / "landing_modules.html").read_text(encoding="utf-8")
PRICING = (TEMPLATES / "landing_pricing.html").read_text(encoding="utf-8")


def test_hero_leads_with_a_customer_outcome():
    assert 'data-customer-outcome="research-to-publication"' in HERO


def test_technical_demo_is_secondary_proof():
    assert 'data-demo-proof="secondary"' in HERO


def test_research_workflow_names_all_four_customer_tasks():
    tasks = set(re.findall(r'data-research-task="([^"]+)"', MODULES))
    assert tasks == {"literature", "analysis", "figures", "manuscript"}


def test_on_premise_is_separate_from_the_app_workflow_cards():
    assert 'data-deployment-option="self-hosted"' in MODULES


def test_pricing_separates_hosted_and_self_hosted_choices():
    plans = (
        "cloud-academic",
        "cloud-professional",
        "self-hosted-community",
        "self-hosted-commercial",
    )
    assert [plan for plan in plans if plan not in PRICING] == []
