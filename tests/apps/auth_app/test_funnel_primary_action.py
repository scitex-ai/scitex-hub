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
SECONDARY_CTA_CLASS = "auth-secondary-cta"
PLATFORM_TAP_FLOOR = 44

OTP_TEMPLATE = REPO / "apps/infra/auth_app/templates/auth_app/email_verification.html"


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


def test_the_otp_steps_two_controls_carry_the_floor_classes():
    """Measured at 390px before this: Verify Email 211x37, Resend Code 97x35."""
    html = OTP_TEMPLATE.read_text()

    verify = [ln for ln in html.splitlines() if "verify-btn" in ln and "<button" in ln]
    resend = [ln for ln in html.splitlines() if "resend-btn" in ln and "<button" in ln]
    assert verify, "the Verify Email button moved — update this guard"
    assert resend, "the Resend Code button moved — update this guard"

    assert CTA_CLASS in verify[0], f"Verify Email has no {CTA_CLASS}: {verify[0].strip()!r}"
    assert SECONDARY_CTA_CLASS in resend[0], (
        f"Resend Code has no {SECONDARY_CTA_CLASS}: {resend[0].strip()!r}"
    )


def test_the_cta_stylesheet_declares_the_platform_tap_floor():
    css = AUTH_CSS.read_text()

    for cls in (CTA_CLASS, SECONDARY_CTA_CLASS):
        # The classes may share one rule; find the rule that mentions this class.
        rules = re.findall(r"([^{}]*\." + cls + r"[\w.-]*[^{}]*)\{([^}]*)\}", css)
        assert rules, f"no rule mentions .{cls} in auth.css"
        bodies = " ".join(body for _sel, body in rules)
        min_height = re.search(r"min-height\s*:\s*(\d+)px", bodies)
        assert min_height, f".{cls} sets no min-height: {bodies!r}"
        assert int(min_height.group(1)) >= PLATFORM_TAP_FLOOR, (
            f".{cls} min-height is {min_height.group(1)}px, below the "
            f"{PLATFORM_TAP_FLOOR}px platform floor"
        )


def test_auth_css_is_actually_loaded_by_the_auth_shell():
    """A rule in a stylesheet nobody links renders nothing — the mistake this
    session already made once on the landing page."""
    base = AUTH_BASE.read_text()

    assert "auth_app/css/auth.css" in base, (
        "auth_base.html no longer links auth.css; the CTA rule would not load"
    )


RETIRED_GREENS = {"#2ea043", "#3fb950", "#2d5a3d", "#3d6a4d", "#5a9a7e", "#198754"}


def _cta_rule_bodies(css, theme):
    """Bodies of every auth.css rule scoping .auth-primary-cta to `theme`."""
    return re.findall(
        r'\[data-theme="'
        + theme
        + r'"\][^{}]*\.auth-primary-cta[^{}]*\{([^}]*)\}',
        css,
    )


def test_the_signup_cta_uses_brand_navy_in_light():
    """Card hub-auth-cta-brand-navy-gold-20261019 (operator CCT4553): the light
    CTA is brand navy consumed as a token, never a green literal."""
    css = AUTH_CSS.read_text()

    bodies = _cta_rule_bodies(css, "light")
    assert bodies, "no light-theme rule scopes .auth-primary-cta in auth.css"
    combined = " ".join(bodies).replace(" ", "").lower()
    assert "var(--color-primary,#1a2a40)" in combined, (
        f"light CTA rule does not consume the brand navy token: {bodies!r}"
    )
    for green in RETIRED_GREENS:
        assert green not in combined, (
            f"light CTA rule still carries retired green {green}: {bodies!r}"
        )


def test_the_signup_cta_uses_brand_gold_in_dark():
    """Same card: the dark CTA is brand gold (hover: active gold), and the
    #1059 vibrant-green override is gone."""
    css = AUTH_CSS.read_text()

    bodies = _cta_rule_bodies(css, "dark")
    assert bodies, "no dark-theme rule scopes .btn.auth-primary-cta in auth.css"
    combined = " ".join(bodies).replace(" ", "").lower()
    assert "var(--color-primary,#d4a87a)" in combined, (
        f"dark CTA rule does not consume the brand gold token: {bodies!r}"
    )
    assert "var(--color-primary-active,#c49868)" in combined, (
        f"dark CTA hover does not deepen to brand active gold: {bodies!r}"
    )
    for green in RETIRED_GREENS:
        assert green not in combined, (
            f"dark CTA rule still carries retired green {green}: {bodies!r}"
        )


def test_the_signin_dark_hover_deepens_to_brand_active_gold():
    """Same card: the shared dark .btn-primary:hover lightens gold toward a
    wash, so the auth form re-scopes its hover to the brand active gold.
    Scoped to .auth-form — no other surface may change."""
    css = AUTH_CSS.read_text()

    rules = re.findall(
        r'\[data-theme="dark"\][^{}]*\.auth-form[^{}]*\.btn-primary:hover[^{}]*\{([^}]*)\}',
        css,
    )
    assert rules, "no dark-theme auth-form-scoped .btn-primary:hover in auth.css"
    combined = " ".join(rules).replace(" ", "").lower()
    assert "var(--color-primary-active,#c49868)" in combined, (
        f"signin dark hover does not deepen to brand active gold: {rules!r}"
    )


def test_the_signin_button_does_not_carry_the_cta_class():
    """The dark CTA override must not leak onto signin: signin stays on the
    tan .btn-primary the operator praised, guarded by selector separation."""
    html = (
        REPO / "apps/infra/auth_app/templates/auth_app/signin.html"
    ).read_text()

    signin_buttons = [ln for ln in html.splitlines() if "<button" in ln and "Sign In" in ln]
    assert signin_buttons, "the Sign In submit button moved — update this guard"
    for line in signin_buttons:
        assert CTA_CLASS not in line, (
            f"Sign In picked up {CTA_CLASS}; the dark green override would leak: "
            f"{line.strip()!r}"
        )
        assert "btn-primary" in line, (
            f"Sign In left btn-primary (the praised tan): {line.strip()!r}"
        )


# EOF
