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

THE GATE IS FAIL-CLOSED, ON PURPOSE, AND IT CLASSIFIES THE RESOLVED ROUTE.
Everything Django does not resolve to a named exempt route is closed to an
account that still owes a payment method — an unresolvable path included.

Classification is by the ROUTE DJANGO RESOLVED, never by the text of the
request. A Django mount is not a string: ``/legal/`` is served by no ``legal``
mount at all, and the same first segment can name an exempt surface AND the
``/<username>/`` product surface (a user whose name is ``legal``, ``i18n``,
``oauth`` or ``billing``). Classifying the text exempted every path BELOW such a
segment too — the bypass this module shipped with. Classifying
``django.urls.resolve(path).route`` asks the only authority that knows which
surface the request actually reached.

The exempt set is small, explicit, and cross-checked against the served URLconf
by an audit that walks the REAL recursive resolver tree
(``tests/apps/accounts_app/test_funnel_product_gate_e2e.py``): a NEW route fails
that audit until somebody classifies it here, and a declaration no route
realizes fails it too. A source-text scan of ``config/urls.py`` could do
neither — it never saw an ``include()``, never saw the mounts
``plugin_urlpatterns()`` inserts, and shared this module's own notion of a
mount, so it stayed green while the gate was wrong.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.urls import Resolver404, resolve, reverse


def _first_segment(route: str | None) -> str:
    """The classification key of a route pattern: its first path segment.

    Route patterns are what Django stores: ``<str:username>/`` (a ``RoutePattern``
    ``_route``) or ``^media/(?P<path>.*)$`` (a ``RegexPattern``), with the mount
    prefix already prepended for an included route. Anchors, the leading and
    trailing slashes and everything after the first ``/`` are not part of the
    key — the same reading the audit in
    ``tests/apps/accounts_app/test_funnel_product_gate_e2e.py`` makes of the
    resolver TREE, so the two can be compared.
    """
    return (route or "").lstrip("^").strip("/").split("/", 1)[0]


#: ``404``-shaped exemption for machine callers: a gated ``/api/`` request gets
#: a JSON refusal instead of a 302 into an HTML page.
API_PREFIXES = ("/api/", "/platform/api/")

#: The ASSET namespaces. These are not Django mounts: in a real deployment the
#: web server serves them and Django never sees the request, and the URLconf
#: only carries a route for them through the DEBUG-only ``static()`` helper
#: (paired with the production-only ``media`` fallback). So the same asset path
#: resolves to a route under ``DEBUG`` and to NOTHING without it, and a gate
#: that answered differently between the two would be measuring the debug flag.
#:
#: Consulted ONLY when ``resolve()`` finds nothing (see
#: :func:`path_is_exempt`), which is what keeps it from re-opening the reviewed
#: bypass: a path Django DOES serve is never classified by its text, so no
#: product route — ``/<username>/`` included, and ``static`` is a legal
#: username — can be exempted through this tuple.
ASSET_PREFIXES = ("/static/", "/media/")

#: Routes a verified-but-unpaid account may still reach. Each entry is the
#: FIRST SEGMENT OF A ROUTE THE SERVED URLCONF REALIZES — a classification
#: (see :func:`route_segment`), never a request-text prefix, and never a
#: leftover:
#:
#: * ``accounts`` — the account's own settings, the payment step and billing;
#: * ``auth``, ``oauth`` — sign in, verify, reset, leave, switch account;
#: * ``billing`` — the funnel's own POST targets (``public_app`` routes);
#: * ``admin`` — staff only, and staff are exempt before this is consulted;
#: * ``healthz``, ``i18n``, ``static``, ``media`` and the PWA/robot files —
#:   infrastructure and assets that gate nothing product-shaped;
#: * ``pricing``, ``landing``, ``terms``, ``privacy``, ``contact`` — the
#:   marketing/legal pages: a person being asked to accept terms before paying
#:   must be able to read them;
#: * ``about``, ``cookies``, ``docs``, ``security``, ``services`` — the
#:   public reference/trust pages, and ``tokushoho-en`` — the English companion
#:   of the JA disclosure below. All six are PUBLIC ROUTES, not product, and
#:   the first cut of this fix wrongly classified them closed (see the review
#:   note under :data:`GATED_MOUNTS`); they were added here by the corrective
#:   change.
#:
#: ``tokushoho`` and ``tokushoho-en`` are a PAIR and are classified together on
#: purpose: the JA page is the legally binding disclosure for Japanese
#: consumers and the EN page is its supplementary translation. Holding one and
#: not the other — which is exactly what the first cut of this fix did — made a
#: legal disclosure reachable in one language and not the other.
#:
#: ``legal`` USED TO BE HERE AND IS DELIBERATELY NOT. No route in the served
#: URLconf is mounted at ``legal/`` — the legal pages are ``terms/``,
#: ``privacy/``, ``tokushoho/``, ``cookies/`` and ``contact/`` — so the entry
#: exempted every request whose first path segment merely READ ``legal``, and
#: ``/legal/`` was served by the ``/<username>/`` product surface. A
#: declaration no route realizes is a phantom, and the audit fails on one.
EXEMPT_MOUNTS = frozenset(
    {
        "accounts",
        "auth",
        "oauth",
        "billing",
        "admin",
        "healthz",
        "i18n",
        "static",
        "media",
        "pricing",
        "landing",
        "terms",
        "privacy",
        "tokushoho",
        "contact",
        "manifest.json",
        "sw.js",
        "favicon.ico",
        "robots.txt",
        # --- public/reference/trust pages and the EN disclosure companion:
        # --- corrected after the independent review of f06cabea found these
        # --- public routes classified product.
        "about",
        "cookies",
        "docs",
        "security",
        "services",
        "tokushoho-en",
    }
)

#: Routes that ARE product, listed for the same reason as the exempt set: the
#: audit names every route the served URLconf realizes, and a new one must be
#: put in one of these two sets deliberately. The list is documentation of a
#: decision, not the enforcement mechanism — the gate closes anything it cannot
#: find in :data:`EXEMPT_MOUNTS`, so a route nobody classified here is already
#: gated (fail-closed); the audit is what turns that silence into a failure.
#:
#: The ``legacy /<app>/`` segments are the ones ``config.urls_legacy_redirects``
#: 301s to ``/apps/<app>/``: they served no product page themselves, but their
#: only destination is a product mount, so they carry the same classification
#: they already had under the first-segment rule, as does every other entry
#: added here when this list was completed against the real resolver tree.
#:
#: CORRECTED AFTER REVIEW. The first cut of this fix (f06cabea) also listed
#: ``about``, ``cookies``, ``docs``, ``security``, ``services`` and
#: ``tokushoho-en`` here and justified it as "the outcome they already had".
#: That was the wrong standard: preserving an outcome is not the same as
#: classifying correctly, and the independent review found the original
#: public/legal accessibility blocker still present — a verified-but-unpaid
#: account was bounced to the payment step when it asked for the about page,
#: the cookie policy, the API docs, the trust page, the services page, or the
#: ENGLISH half of the disclosure whose JAPANESE half was reachable. They are
#: public routes, they belong in :data:`EXEMPT_MOUNTS`, and they were moved
#: there. What stays here is the classification the resolver supports:
#: ``/docs/web-api/`` is public, and the legacy ``/docs/`` redirect to the
#: ``/apps/docs/`` product mount rides along with it (a 301 is not product, and
#: its destination is gated on the next request).
GATED_MOUNTS = frozenset(
    {
        "",  # the workspace root (root_dispatch)
        "<str:username>",  # the per-user project surface
        "dev__<str:rest>",
        "chat",
        "console",
        "files",
        "apps",
        "new",
        "current-project",
        "search",
        "social",
        "dev",
        "ai-setup",
        "integrations",
        "organizations",
        "project",
        "invitations",
        "api",
        "platform",
        # --- present in the served URLconf, classified when the audit was
        # --- completed against the real resolver tree ---
        ".well-known",
        "__reload__",
        "api-docs",
        "api-keys",
        "clew",
        "cloud",
        "contributors",
        "demo",
        "demos",
        "donate",
        "enter",
        "example",
        "figrecipe",
        # --- added at the current-base merge of develop (#948's internal demo
        # --- library: ``public_app:internal_demos`` and ``internal_demo_media``).
        # --- The audit failed on this segment once develop was merged, because a
        # --- route nobody classified is exactly what it is there to catch. It was
        # --- ALREADY gated (an undeclared segment is closed, fail-closed), so
        # --- declaring it here records the decision rather than changing it.
        # --- This is not a public surface, so it is not in the residual
        # --- public-page family listed in this same set: the view denies a
        # --- logged-out visitor outright (302 -> /auth/login/?next=...), denies
        # --- a signed-in non-staff account (403), and serves the library only to
        # --- instance admins.
        "internal",
        "keyboard-shortcuts",
        "llm",
        "notebook",
        "open-source",
        "publications",
        "recruit",
        "releases",
        "scholar",
        "server-status",
        "setup",
        "status",
        "tools",
        "v1",
        "workspace",
        "writer",
    }
)


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


def route_segment(path: str):
    """First segment of the route Django actually resolves ``path`` to.

    ``None`` when nothing serves the path. This is the ONLY classification key
    the gate uses: the route Django resolved, read off
    ``ResolverMatch.route``, not the text the client typed. Computed from the
    route for the same reason :func:`path_is_exempt` documents — a first path
    segment is not a mount.
    """
    try:
        match = resolve(path)
    except Resolver404:
        return None
    return _first_segment(match.route)


def path_is_exempt(path: str) -> bool:
    """Whether ``path`` is on the exempt side of the gate classification.

    Classification is by the FIRST SEGMENT OF THE ROUTE DJANGO RESOLVED, not of
    the request text. ``/legal/`` reads like an exempt mount and is served by
    the ``/<username>/`` product surface; ``/i18n/``, ``/oauth/`` and
    ``/billing/`` likewise. Reading the text exempted all of them, and every
    path below them.

    The one text-keyed exemption is an ASSET namespace when nothing resolves at
    all (:data:`ASSET_PREFIXES`) — a path the web server serves, or that
    nothing serves, never a route. A path Django DOES serve is classified by the
    route, so ``/static/x/``, which resolves to the ``/<username>/`` surface, is
    product even though it reads like an asset.
    """
    segment = route_segment(path)
    if segment is None:
        return (path or "").startswith(ASSET_PREFIXES)
    return segment in EXEMPT_MOUNTS


def request_is_gated(path: str) -> bool:
    """THE gate: may an account that owes a payment method reach ``path``?

    Fail-closed: a path is closed unless the route Django resolved for it is
    named in :data:`EXEMPT_MOUNTS`, so an unclassified route and a request whose
    text merely LOOKS exempt are both closed. A path nothing serves is closed
    too, except inside an asset namespace — see :func:`path_is_exempt` for why
    that one is not a mount and cannot be product. The other carve-out is that
    an anonymous request never reaches here at all (middleware checks
    authentication first), so public marketing pages are unaffected.
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
    "ASSET_PREFIXES",
    "EXEMPT_MOUNTS",
    "GATED_MOUNTS",
    "first_product_url",
    "gated_response_for",
    "path_is_exempt",
    "payment_step_url",
    "request_is_gated",
    "route_segment",
]
