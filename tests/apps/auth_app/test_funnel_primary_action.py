#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The button that finishes account creation must be a real touch target.

Card: hub-signup-email-stripe-funnel-20260917. SSOT §4 puts the platform's floor at
44px targets.

Measured on the running Hub (chromium, 2026-09-17) before this change:

    "Create Account" submit button: 42px tall at 1440x900, 33px at 390x844

the smallest screen carrying the smallest version of the funnel's single most
important control. It is a Bootstrap `.btn btn-success w-100` with no rule of its
own, so nothing in the repo held it to the platform floor.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SIGNUP = REPO / "apps/infra/auth_app/templates/auth_app/signup.html"
AUTH_CSS = REPO / "apps/infra/auth_app/static/auth_app/css/auth.css"
AUTH_BASE = REPO / "apps/infra/auth_app/templates/auth_app/auth_base.html"

CTA_CLASS = "auth-primary-cta"
PLATFORM_TAP_FLOOR = 44


def test_the_create_account_button_carries_the_cta_class():
    html = SIGNUP.read_text()

    # The label lives inside {% trans "Create Account" %}, so match the button line
    # rather than trying to parse the tag from both sides.
    buttons = [
        line for line in html.splitlines()
        if "<button" in line and "Create Account" in line
    ]
    assert buttons, "the Create Account submit button moved — update this guard"
    assert CTA_CLASS in buttons[0], (
        f"the signup CTA has no {CTA_CLASS} class, so nothing holds it to 44px: "
        f"{buttons[0].strip()!r}"
    )


def test_the_cta_stylesheet_declares_the_platform_tap_floor():
    css = AUTH_CSS.read_text()

    rule = re.search(rf"\.[\w.-]*{CTA_CLASS}\s*\{{([^}}]*)\}}", css)
    assert rule, f"no rule for .{CTA_CLASS} in auth.css"

    body = rule.group(1)
    min_height = re.search(r"min-height\s*:\s*(\d+)px", body)
    assert min_height, f".{CTA_CLASS} sets no min-height: {body!r}"
    assert int(min_height.group(1)) >= PLATFORM_TAP_FLOOR, (
        f".{CTA_CLASS} min-height is {min_height.group(1)}px, below the "
        f"{PLATFORM_TAP_FLOOR}px platform floor"
    )


def test_auth_css_is_actually_loaded_by_the_auth_shell():
    """A rule in a stylesheet nobody links renders nothing — the mistake this
    session already made once on the landing page."""
    base = AUTH_BASE.read_text()

    assert "auth_app/css/auth.css" in base, (
        "auth_base.html no longer links auth.css; the CTA rule would not load"
    )


# EOF
