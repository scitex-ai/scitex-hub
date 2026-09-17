#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Card-required onboarding, enforced server-side.

Card: hub-card-required-entitlement-gate-20260917 (follows PR #934, whose payment step
is the browser-visible half). Until this existed, the funnel was a funnel and not a
boundary: a verified user with no usable card could type an app URL and be served.

The rule, as decided with the operator:

* an authenticated user WITHOUT a usable, webhook-confirmed card cannot enter normal app
  routes - the request is redirected to the payment step;
* only billing, the payment step, auth, legal/support and the Stripe return + webhook
  routes are reachable without one. The list is CLOSED: a route added later is gated by
  default, which is the only safe direction for an entitlement check;
* entitlement is the SAME fact the rest of the hub reads:
  ``payment_methods.filter(is_usable=True, is_default=True)``. ``is_usable`` is only
  ever flipped by the SIGNED ``checkout.session.completed`` webhook (see
  ``services/stripe_setup.py``), so nothing a browser can do - including coming back
  from a successful-looking Stripe redirect - grants entitlement;
* staff are exempt, so the people who operate a locked-down deployment can still reach
  the surfaces they are operating;
* anonymous requests are left to the auth layer. Sending a visitor to the PAYMENT step
  would ask for a card before an account exists.

Why a module and not a middleware body: the decision is a pure function of a path and
the user's facts, so it is testable with no database and no request, and the middleware
stays a thin adapter over it.
"""

from __future__ import annotations

from typing import Optional, Tuple

#: The request may proceed.
OPEN = "open"
#: The request must go to the payment step instead.
GATED = "gated"

#: Where a gated user is sent. The step itself is on the allowlist, or the redirect
#: would loop: gate -> step -> gate -> step.
PAYMENT_STEP_PATH = "/accounts/settings/payment/"

#: Paths reachable WITHOUT a usable card. Prefix matches, and the trailing slash is
#: load-bearing: "/auth/" must not admit "/authbypass/".
REACHABLE_WITHOUT_CARD = (
    # the payment step and the billing flow it hands over to
    PAYMENT_STEP_PATH,
    "/accounts/settings/billing/",
    "/billing/",
    # auth: login, logout, signup, OTP, reset, social callbacks
    "/auth/",
    "/accounts/oauth/",
    # legal, support, contact
    "/legal/",
    "/terms/",
    "/privacy/",
    "/cookies/",
    "/support/",
    "/contact/",
    # the page cannot render without these
    "/static/",
    "/media/",
    "/favicon.ico",
    "/healthz",
)


def path_is_reachable_without_card(path: str) -> bool:
    """Whether ``path`` is on the closed allowlist."""
    if not path:
        return False
    return any(path.startswith(prefix) for prefix in REACHABLE_WITHOUT_CARD)


def has_usable_card(user) -> bool:
    """The hub's one definition of "a card we can charge", read, never recomputed.

    ``is_usable`` is set by the signed webhook only; ``is_default`` is the card the
    user chose. Both are required, exactly as ``stripe_provider`` requires them, so this
    gate can never disagree with the billing code about who has a card.
    """
    methods = getattr(user, "payment_methods", None)
    if methods is None:
        return False
    try:
        return bool(methods.filter(is_usable=True, is_default=True).exists())
    except Exception:  # noqa: BLE001 - a user without the relation is card-less
        return False


def is_exempt(user) -> bool:
    """Staff and superusers are never gated; anonymous is the auth layer's problem."""
    if not getattr(user, "is_authenticated", False):
        return True
    return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))


def card_required_decision(path: str, user) -> Tuple[str, Optional[str]]:
    """``(OPEN, None)`` or ``(GATED, payment_step_path)`` for one request."""
    if is_exempt(user):
        return OPEN, None
    if path_is_reachable_without_card(path):
        return OPEN, None
    if has_usable_card(user):
        return OPEN, None
    return GATED, PAYMENT_STEP_PATH


# EOF
