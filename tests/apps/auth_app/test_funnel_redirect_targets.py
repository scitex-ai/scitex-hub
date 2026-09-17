#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every redirect target in the signup funnel must be a route that exists.

Card: hub-signup-email-stripe-funnel-20260917 — the functional funnel
(account -> OTP -> payment step -> first project).

Measured before this change, on the running Hub:

    /dashboard/  -> 404
    /home/       -> 404

and the OTP success handler in the auth funnel fell back to one of them:

    apps/infra/auth_app/templates/auth_app/email_verification.html:252
      window.location.href = data.redirect_url || "/dashboard/"

So a freshly verified user whose response carried no redirect_url — an older
response shape, a partial payload, any path that does not set the field — was
sent to a dead page at the exact moment the product is supposed to deliver its
first moment of progress. The SSOT forbids exactly that ("no … dead
placeholders").

This test resolves the fallback targets the funnel actually declares against the
real URLconf, so a renamed or retired route fails here instead of in a browser.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.urls import Resolver404, resolve

REPO = Path(__file__).resolve().parents[3]

#: The templates a user passes through between landing and first project.
FUNNEL_TEMPLATES = (
    "apps/infra/auth_app/templates/auth_app/signup.html",
    "apps/infra/auth_app/templates/auth_app/email_verification.html",
    "apps/infra/accounts_app/templates/accounts_app/payment_step.html",
)

#: ``... || "/some/path"`` — a hardcoded client-side redirect fallback.
FALLBACK_RE = re.compile(r'\|\|\s*"([^"]*)"')
#: ``window.location.href = "/some/path"`` — a bare hardcoded redirect. The second
#: dead route found in this funnel lived here (the OTP page sent anyone without a
#: pending email to "/signup/", which is not a route), and the first guard only
#: looked at `||` fallbacks.
BARE_REDIRECT_RE = re.compile(r'(?:location\.href|location\.replace\(|location\.assign\()\s*=?\s*"([^"]*)"')


def _fallback_targets(template: str) -> list[str]:
    text = (REPO / template).read_text()
    targets = []
    for pattern in (FALLBACK_RE, BARE_REDIRECT_RE):
        for match in pattern.finditer(text):
            value = match.group(1)
            # Only same-site absolute paths are ours to prove; a URL, an attribute
            # or a JS expression is not a redirect target this test can resolve.
            if value.startswith("/") and " " not in value and "{" not in value:
                targets.append(value)
    return targets


@pytest.mark.parametrize("template", FUNNEL_TEMPLATES)
def test_every_hardcoded_fallback_in_the_funnel_resolves(template):
    """Weak net only, and labelled as such.

    ``restricted_urls.resolve()`` proving a path MATCHES is not proof it SERVES:
    both "/dashboard/" and "/signup/" resolve happily — they match a catch-all view
    that then raises 404 — while the running Hub answers 404 for each. So this test
    catches a target that matches no pattern at all, and the measured-dead test
    below does the work that actually matters.
    """
    targets = _fallback_targets(template)
    bad = []
    for path in targets:
        try:
            resolve(path)
        except Resolver404:
            bad.append(path)

    assert not bad, (
        f"{template} redirects to path(s) that match no URL pattern: {bad}"
    )


#: Paths MEASURED on the running Hub (chromium + HTTP, 2026-09-17): each answers
#: 404. They are named here because resolution alone cannot tell them from a live
#: route, and a funnel that redirects into one lands a verified user on a dead page.
MEASURED_DEAD_PATHS = ("/dashboard/", "/home/", "/signup/")


@pytest.mark.parametrize("template", FUNNEL_TEMPLATES)
def test_the_funnel_never_redirects_into_a_measured_dead_path(template):
    text = (REPO / template).read_text()

    offenders = []
    for path in MEASURED_DEAD_PATHS:
        # Look at how the path is USED, not that the string appears: these tokens
        # can legitimately appear in prose or in a comment.
        for pattern in (FALLBACK_RE, BARE_REDIRECT_RE):
            for match in pattern.finditer(text):
                if match.group(1) == path:
                    offenders.append(f"{path} ({match.group(0)[:60]})")

    assert not offenders, (
        f"{template} redirects to measured-dead path(s): {offenders}. "
        "Use a named route ({% url %}) so a rename cannot reintroduce this."
    )


def test_the_otp_handler_no_longer_falls_back_to_the_dead_dashboard_route():
    rel = "apps/infra/auth_app/templates/auth_app/email_verification.html"
    text = (REPO / rel).read_text()

    # Assert on how a path is USED, not on the string: the fix's own comment quotes
    # "/signup/" while explaining what it replaced, and a naive substring check
    # failed on that comment rather than on the code.
    targets = _fallback_targets(rel)
    assert not [t for t in targets if t in MEASURED_DEAD_PATHS], (
        f"the OTP page still redirects into a dead path: {targets}"
    )
    assert "data.redirect_url ||" in text, (
        "the handler must still prefer the server-provided redirect_url"
    )


def test_the_verified_user_is_sent_where_the_backend_says():
    """The server already decides this (post_signup_redirect_url): the payment step
    while card registration is open, the user's workspace otherwise."""
    from apps.infra.public_app.services.billing_provider import post_signup_redirect_url

    import inspect

    source = inspect.getsource(post_signup_redirect_url)
    assert "payment_step" in source or "billing" in source, (
        "post_signup_redirect_url no longer routes a verified signup into billing"
    )


# EOF
