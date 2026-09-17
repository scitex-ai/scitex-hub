#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The signup funnel's navigation, and the product gate it enforces.

Card: hub-signup-email-stripe-funnel-20260917. PR #934 review, blocker 1.

Two questions live here, and both are answered in ONE place so the funnel
cannot develop a second opinion about either:

1. **Where does the funnel send someone?** :func:`payment_step_url` for the
   step, :func:`first_product_url` for the moment the provider has confirmed
   the trial. Blocker 3 was that Stripe returned the browser to a generic
   billing page the step itself never reads — success and cancel therefore
   landed the user on a surface that could not tell them what happened.
2. **May this account reach the product at all?** :func:`request_is_gated`,
   consulted by ``apps.infra.accounts_app.middleware.OnboardingGateMiddleware``.

THE GATE IS FAIL-CLOSED, ON PURPOSE. Everything not named in
:data:`EXEMPT_MOUNTS` is closed to an account that still owes a payment method.
A deny-list of "product" paths would have to be re-derived every time a leaf
app is mounted, and the one that gets forgotten is the bypass — which is exactly
how the reviewed defect shipped. The exempt set is small, explicit, and
cross-checked against ``config/urls.py`` by a test: a NEW top-level mount fails
that test until somebody classifies it here.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.urls import reverse

#: ``404``-shaped exemption for machine callers: a gated ``/api/`` request gets
#: a JSON refusal instead of a 302 into an HTML page.
API_PREFIXES = ("/api/", "/platform/api/")

#: Mounts a verified-but-unpaid account may still reach. Each entry is a
#: deliberate classification, not a leftover:
#:
#: * ``/accounts/`` — the account's own settings, the payment step and billing;
#: * ``/auth/``, ``/oauth/`` — sign in, verify, reset, leave, switch account;
#: * ``/billing/`` — the funnel's own POST targets (``public_app`` routes);
#: * ``/admin/`` — staff only, and staff are exempt before this is consulted;
#: * ``/healthz/``, ``/i18n/``, ``/static/``, ``/media/`` and the PWA/robot
#:   files — infrastructure and assets that gate nothing product-shaped;
#: * the legal/marketing pages — a person being asked to pay must be able to
#:   read the terms they are accepting.
EXEMPT_MOUNTS = frozenset(
    {
        "accounts/",
        "auth/",
        "oauth/",
        "billing/",
        "admin/",
        "healthz/",
        "i18n/",
        "static/",
        "media/",
        "pricing",
        "landing",
        "legal",
        "terms",
        "privacy",
        "tokushoho",
        "contact",
        "manifest.json",
        "sw.js",
        "favicon.ico",
        "robots.txt",
    }
)

#: Mounts that ARE product, listed for the same reason as the exempt set: the
#: classification test names every top-level mount in ``config/urls.py``, and a
#: new one must be put in one of these two sets deliberately.
GATED_MOUNTS = frozenset(
    {
        "",  # the workspace root (root_dispatch)
        "chat/",
        "console/",
        "files/",
        "apps/",
        "new/",
        "current-project/",
        "search/",
        "social/",
        "dev/",
        "ai-setup/",
        "integrations/",
        "organizations/",
        "project/",
        "invitations/",
        "api/",
        "platform/api/",
        "<str:username>/",  # the per-user project surface
        "dev__<str:rest>/",
    }
)


#: First path segment of every exempt mount — the form the gate compares
#: against (see :func:`path_is_exempt`).
_EXEMPT_HEADS = frozenset(mount.strip("/") for mount in EXEMPT_MOUNTS)


def payment_step_url(**query) -> str:
    """The funnel's own address. One helper, so no surface hand-builds it."""
    url = reverse("accounts_app:payment_step")
    if query:
        url = f"{url}?{urlencode(query)}"
    return url


def first_product_url() -> str:
    """Where a provider-confirmed account goes: its first project.

    The funnel's whole purpose is that a person who has just entered a card
    ends up somewhere they can DO something. ``project_create`` is that route.
    """
    return reverse("project_create")


def path_is_exempt(path: str) -> bool:
    """Whether ``path`` is on the exempt side of the gate classification.

    Classification is by the FIRST path segment, which is what a Django mount
    is. The root ("/") is deliberately not exempt: it is the workspace, i.e.
    the first thing the gate exists to hold back.
    """
    stripped = (path or "").strip("/")
    if not stripped:
        return False
    return stripped.split("/", 1)[0] in _EXEMPT_HEADS


def request_is_gated(path: str) -> bool:
    """THE gate: may an account that owes a payment method reach ``path``?

    Fail-closed: anything this module cannot classify as exempt is closed. The
    one carve-out is that an anonymous request never reaches here at all
    (middleware checks authentication first), so public marketing pages are
    unaffected.
    """
    return not path_is_exempt(path)


def gated_response_for(request):
    """The refusal for a gated request, shaped for the caller.

    A machine caller (``/api/``) is answered with JSON so it fails loudly
    instead of trying to render a login-shaped HTML page; a browser is sent to
    the step, which is the surface that tells it what to do next.
    """
    from django.http import JsonResponse
    from django.shortcuts import redirect

    if any(request.path.startswith(prefix) for prefix in API_PREFIXES):
        return JsonResponse(
            {
                "error": "payment_required",
                "detail": (
                    "This account is inside the signup funnel and owes a payment "
                    "method. Finish the payment step before using the API."
                ),
                "payment_step": payment_step_url(),
            },
            status=402,
        )
    return redirect(payment_step_url(next=request.get_full_path()))


__all__ = [
    "API_PREFIXES",
    "EXEMPT_MOUNTS",
    "GATED_MOUNTS",
    "first_product_url",
    "gated_response_for",
    "path_is_exempt",
    "payment_step_url",
    "request_is_gated",
]
