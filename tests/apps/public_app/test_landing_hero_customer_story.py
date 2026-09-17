#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The landing hero sells the outcome, not the machinery.

Card: hub-landing-customer-story-20260917 (walkthrough 7924-7928).
SSOT: docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md §1 — "Lead with the customer
outcome: one connected workspace from literature to a publication-ready paper",
"Present workflow tasks before internal product names", "Keep the timed demo as
secondary evidence. Label measured workflow time and playback duration
separately; move MCP details into a technical section."

Measured on the running Hub (dev), 2026-09-17, before this change:
  * the hero had NO <h1> at all — the largest thing a customer read was a logo
    image plus the generic site tagline;
  * the first proof it offered was "Automated Research with SciTeX MCP Server in
    40 min", with a "Speed: 8x" control beside it — one number for two different
    things (how long the research took, and how fast the video plays).

The rendering tests below need no database; the URLconf tests are gated for CI.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.template.loader import render_to_string

HERO = "public_app/landing_partials/landing_hero.html"

HERO_CONTEXT = {
    "SITE_TAGLINE": "Open-source Ecosystem for Scientific Research",
    "SCITEX_HUB_VERSION": "0.0.0-test",
    "CONTACT_EMAIL": "info@scitex.ai",
}

# The four tasks the hero must name, in customer language.
OUTCOME_TASKS = ("literature", "data", "figure", "manuscript")


def _render_hero() -> str:
    """Hero markup with HTML comments removed.

    The template keeps commented-out headline options ("for future use"), and the
    first version of these tests matched one of them — a test that asserts on
    markup no visitor ever sees proves nothing.
    """
    html = render_to_string(HERO, HERO_CONTEXT)
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


# ---------------------------------------------------------------------------
# outcome-first hero (no database needed)
# ---------------------------------------------------------------------------


def test_the_hero_has_a_headline_that_names_the_customer_outcome():
    html = _render_hero()

    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    assert h1, "the hero has no <h1>: the first thing a customer reads is a logo"

    text = re.sub(r"\s+", " ", _strip_tags(h1.group(1))).strip().lower()
    assert "project" in text or "workspace" in text, (
        f"the headline does not describe the one-workspace model: {text!r}"
    )


def test_the_hero_names_literature_data_figures_and_manuscripts():
    text = re.sub(r"\s+", " ", _strip_tags(_render_hero())).lower()

    missing = [task for task in OUTCOME_TASKS if task not in text]
    assert not missing, f"the hero never mentions {missing}"


def test_the_hero_does_not_lead_with_the_internal_product_names():
    """Tasks before product names: the apps may be linked, not sold first."""
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", _render_hero(), re.S)
    assert h1
    headline = _strip_tags(h1.group(1)).lower()

    for internal in ("scholar", "writer", "figrecipe", "mcp"):
        assert internal not in headline, (
            f"the headline leads with the internal name {internal!r}: {headline!r}"
        )


# ---------------------------------------------------------------------------
# the demo is secondary evidence, and its two numbers are told apart
# ---------------------------------------------------------------------------


def test_the_demo_card_title_is_outcome_first_and_mcp_free():
    html = _render_hero()

    block = re.search(r'<div class="demo-description">(.*?)</div>\s*<a', html, re.S)
    assert block, "the demo card has no description block to check"
    # Whole description block, tags stripped: the first version of this test
    # stopped at the "DEMO" badge's closing </span> and asserted on that.
    text = re.sub(r"\s+", " ", _strip_tags(block.group(1))).strip()

    assert "MCP" not in text, (
        "the demo card still leads with the MCP server: MCP belongs in a "
        f"technical section, not the pitch ({text!r})"
    )
    assert not re.search(r"in\s*40\s*min", text, re.I), (
        f"the demo card still states a duration as its selling point ({text!r})"
    )


def test_measured_workflow_time_and_playback_speed_are_labelled_separately():
    html = _render_hero()

    assert re.search(r'data-demo-workflow-time="[^"]+"', html), (
        "the recorded workflow time is not labelled as such"
    )
    assert re.search(r'class="speed-label"[^>]*>\s*{%|Playback', html) or "Playback" in html, (
        "the speed control is not labelled as playback"
    )
    # The 40-minute figure must sit inside the workflow-time label, not float free.
    workflow = re.search(r'data-demo-workflow-time="([^"]+)"', html)
    assert workflow and "40" in workflow.group(1), (
        "the measured workflow time does not carry the recorded figure"
    )


def test_mcp_details_are_offered_as_a_technical_secondary_link():
    html = _render_hero()

    link = re.search(r'data-demo-technical="true"[^>]*href="([^"]+)"', html)
    if not link:
        link = re.search(r'href="([^"]+)"[^>]*data-demo-technical="true"', html)
    assert link, "there is no technical secondary link for MCP/API details"
    assert "/docs/" in link.group(1), (
        f"the technical link does not point at the docs ({link.group(1)!r})"
    )


def test_new_selectors_are_defined_in_a_stylesheet_the_landing_page_loads():
    """A rule in an unloaded stylesheet is a rule no browser ever sees.

    Written after exactly that mistake: `.demo-workflow-time` was first added to
    `public_app/css/landing-hero-demo.css`, which nothing references and which is
    absent from the rendered page's stylesheet list. This test resolves the
    stylesheets the landing TEMPLATE actually links and requires the new
    selectors to be defined in one of them.
    """
    repo = Path(__file__).resolve().parents[3]
    landing_tpl = repo / "apps/infra/public_app/templates/public_app/landing.html"
    hero_tpl = repo / "apps/infra/public_app/templates/public_app/landing_partials/landing_hero.html"

    linked = re.findall(r"{%\s*static\s+'([^']+\.css)'\s*%}", landing_tpl.read_text())
    assert linked, "no stylesheets found in the landing template"

    roots = [
        repo / "apps/infra/public_app/static",
        repo / "static",
    ]
    loaded: dict[str, str] = {}
    for rel in linked:
        for root in roots:
            candidate = root / rel
            if candidate.is_file():
                loaded[rel] = candidate.read_text()
                break

    assert loaded, "none of the landing stylesheets could be resolved"

    # Selectors the new hero markup depends on, and where they must not be.
    required = (".demo-workflow-time", ".demo-technical-link")
    combined = "\n".join(loaded.values())
    missing = [sel for sel in required if sel not in combined]
    assert not missing, (
        f"{missing} are not defined in any stylesheet the landing page loads "
        f"(loaded: {sorted(loaded)})"
    )

    assert "landing-hero-demo.css" not in loaded, (
        "landing-hero-demo.css started being loaded — re-check which copy of the "
        "demo-card rules wins"
    )
    assert hero_tpl.is_file()


# ---------------------------------------------------------------------------
# the same contract through the real URLconf (database gate, runs in CI)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLandingRouteCarriesTheCustomerStory:
    def test_landing_page_hero_leads_with_the_outcome(self):
        from django.test import Client

        response = Client().get("/landing/")
        assert response.status_code == 200
        content = response.content.decode()

        assert "<h1" in content, "the rendered landing page has no <h1> in its hero"
        assert "MCP Server in 40 min" not in content


# EOF
