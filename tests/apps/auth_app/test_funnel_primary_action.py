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


MUTED_DARK_SUCCESS = {"#2d5a3d", "#3d6a4d"}


def test_the_signup_cta_has_its_own_dark_theme_green():
    """Card hub-signup-cta-washed-out-olive-dark-20261007: the shared dark
    .btn-success rule is a muted olive that reads as disabled on black, so
    the signup CTA needs its own dark-theme green scoped to .auth-primary-cta.
    """
    css = AUTH_CSS.read_text()

    dark_cta = re.findall(
        r'\[data-theme="dark"\]\s*\.btn\.auth-primary-cta[^{}]*\{([^}]*)\}',
        css,
    )
    assert dark_cta, "no dark-theme rule scopes .btn.auth-primary-cta in auth.css"
    bodies = " ".join(dark_cta)
    assert "#2ea043" in bodies.replace(" ", "").lower() or "#3fb950" in bodies.replace(
        " ", ""
    ).lower(), f"dark CTA rule sets no vibrant green: {bodies!r}"
    for muted in MUTED_DARK_SUCCESS:
        assert muted not in bodies.replace(" ", "").lower(), (
            f"dark CTA rule reuses the muted olive {muted} it was written to escape"
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
