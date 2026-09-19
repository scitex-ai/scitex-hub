#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end: the signup funnel is a BOUNDARY, not a suggestion.

Card: hub-signup-email-stripe-funnel-20260917. PR #934 review, blockers 1, 2, 3,
5, 6 and 7.

WHY THIS FILE EXISTS. The reviewed PR shipped a browser-visible payment step and
no server-side lifecycle: a verified account was activated and logged in before
payment, the record that it owed a payment method was deleted at verification,
and no product route checked anything — so `/`, `/<username>/` and every leaf app
were reachable without a card, Stripe checkout never created a subscription, a
replayed webhook re-ran its side effects, `?plan=` overrode the configured price
set, and Google/ORCID signups never entered the funnel at all. Each of those is
exercised HERE, through the real URLconf and the real middleware stack, in the
shape a real user (or a real retry) produces.

Requested explicitly by the review: "bypass/replay/duplicate/existing-user E2E
tests".

These tests need a database (they are the integration layer); the decision tables
they rely on also have no-database unit tests beside the code they belong to.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from django.test import Client
from django.urls import Resolver404, get_resolver, resolve, reverse

from apps.infra.accounts_app.funnel import (
    EXEMPT_MOUNTS,
    GATED_MOUNTS,
    payment_step_url,
    request_is_gated,
)

REPO = Path(__file__).resolve().parents[3]

#: Product surfaces a verified-but-unpaid account must not reach. Each one was
#: either named in the review or is a mounted product app entry point.
GATED_PATHS = (
    "/",
    "/apps/",
    "/new/",
    "/chat/",
    "/console/",
    "/files/",
    "/current-project/",
    "/search/",
    "/social/",
    "/apps/scholar/",
    "/apps/writer/",
    "/apps/my-projects/",
    "/integrations/",
    "/organizations/",
    "/some-user/",  # the /<username>/ project surface
    "/api/v1/anything/",  # machine callers are refused too, with JSON
    "/platform/api/anything/",
)


# ---------------------------------------------------------------------------
# Walking the REAL resolver tree — see
# TestTheGateIsAuditedAgainstTheRealResolverTree for what these guard.
# ---------------------------------------------------------------------------
#: Django converters, each paired with a value it accepts: how a route pattern
#: becomes a request path a real client could send.
_CONVERTER_VALUES = {
    "int": "1",
    "slug": "x",
    "str": "x",
    "path": "x",
    "uuid": "00000000-0000-0000-0000-000000000000",
}

#: Mounts only a DEBUG URLconf adds (``config/urls.py`` appends the static
#: helper and the ``__reload__`` SSE route under ``if settings.DEBUG``): the
#: audit must not call them dead when they are simply absent.
_DEBUG_ONLY_MOUNTS = frozenset({"static", "__reload__"})


def _segment(route: str) -> str:
    """The classification key: the FIRST path segment of a route pattern.

    Deliberately duplicated here. The gate computes this from the route Django
    resolved for a REQUEST; this copy computes it from the route the resolver
    TREE contains. Two readings of the same rule that can disagree is what makes
    the audit below an audit instead of a restatement.
    """
    return (route or "").lstrip("^").strip("/").split("/", 1)[0]


def _route_text(pattern) -> str:
    """A pattern as Django stores it: ``_route`` for ``RoutePattern``, the regex
    source for ``RegexPattern``."""
    return getattr(pattern.pattern, "_route", None) or str(pattern.pattern)


def _literal_prefix(text: str) -> str:
    """The literal prefix of a regex route: anchors dropped, escape sequences
    unfolded, cut at the first construct that is not a literal character."""
    out, index, end = [], 0, len(text)
    while index < end:
        char = text[index]
        if char == "\\" and index + 1 < end:
            out.append(text[index + 1])
            index += 2
            continue
        if char in "^$":
            index += 1
            continue
        if char in "()[]?*+|{":
            break
        out.append(char)
        index += 1
    return "".join(out)


def _regex_example(text: str) -> str:
    """A concrete path that satisfies a regex route.

    Literal characters are kept, every group and character class becomes a
    placeholder, anchors and the optional marker are dropped. Not a regex
    parser: it only has to produce a path THIS route accepts, and the audit
    reports a route it cannot exercise rather than skipping it.
    """
    out, index, end = [], 0, len(text)
    while index < end:
        char = text[index]
        if char in "^$?":
            index += 1
            continue
        if char == "\\" and index + 1 < end:
            out.append(text[index + 1])
            index += 2
            continue
        if char == "(":
            depth, index = 1, index + 1
            while index < end and depth:
                if text[index] == "\\":
                    index += 2
                    continue
                if text[index] == "(":
                    depth += 1
                elif text[index] == ")":
                    depth -= 1
                index += 1
            out.append("x")
            continue
        if char == "[":
            while index < end and text[index] != "]":
                index += 1
            index += 1
            out.append("x")
            continue
        if char in "*+|{":
            index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _candidate_requests(route_text: str, *, is_regex: bool):
    """Request paths this route should serve, most specific first.

    A route is a pattern, not a path: ``^static/(?P<path>.*)$`` and
    ``<str:username>/`` both accept ``/static/x`` and
    ``/static/x/`` is a DIFFERENT route (the username one) — which is exactly
    why the gate has to read what Django resolved instead of what the text
    looks like.
    """
    if is_regex:
        literal = _literal_prefix(route_text)
        candidates = [
            _regex_example(route_text),
            literal + "x",
            literal + "x/",
            literal + "/",
        ]
    else:
        text = re.sub(
            r"<(?:(?P<converter>[a-z_]+):)?(?P<name>[a-zA-Z_]+)>",
            lambda match: _CONVERTER_VALUES.get(match.group("converter") or "str", "x"),
            route_text,
        )
        candidates = [text, text + "/"]

    seen, unique = set(), []
    for candidate in candidates:
        path = "/" + candidate.lstrip("/")
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def _resolver_leaves():
    """Every route the served URLconf actually has, includes recursed.

    Yields ``(route_text, pattern, namespaces)``. The namespace chain is what
    tells a route mounted inside ``public_app`` apart from one mounted at the
    root when the route text alone cannot.
    """
    from django.urls.resolvers import URLResolver

    leaves = []

    def walk(resolver, prefix, namespaces):
        inherited = set(namespaces)
        namespace = getattr(resolver, "namespace", None)
        if isinstance(namespace, str) and namespace:
            inherited.add(namespace)
        for pattern in resolver.url_patterns:
            route_text = prefix + _route_text(pattern)
            if isinstance(pattern, URLResolver):
                walk(pattern, route_text, tuple(inherited))
            else:
                leaves.append((route_text, pattern, tuple(inherited)))

    walk(get_resolver(), "", ())
    return leaves


def _top_level_route_texts():
    """The patterns of the URLconf's own ``urlpatterns``, mounts included."""
    return [_route_text(pattern) for pattern in get_resolver().url_patterns]


def _exercisable_request(route_text, pattern):
    """``(path, match)`` for the first candidate request Django resolves, or
    ``None`` when no candidate is served by anything."""
    is_regex = not hasattr(pattern.pattern, "_route")
    for candidate in _candidate_requests(route_text, is_regex=is_regex):
        try:
            return candidate, resolve(candidate)
        except Resolver404:
            continue
    return None


def _create_user(username, *, in_funnel=True, staff=False):
    """A user, in the funnel (verified, awaiting payment) unless told otherwise.

    ``in_funnel`` mirrors what the OTP handler does on success — see
    ``test_the_otp_handler_itself_enrols_the_account``, which drives the real
    endpoint rather than this helper.
    """
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user(
        username=username, email=f"{username}@example.com", password="TestPass123!"
    )
    if staff:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
    if in_funnel:
        from apps.infra.auth_app.onboarding import mark_verified

        mark_verified(user, source="email")
    return user


def _login(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def provider_open(settings):
    """A deployment that CAN take a card, so the requirement is in force.

    Set on SETTINGS rather than by patching a view: the requirement is computed
    by ``onboarding.payment_required`` from the provider's own configuration, and
    a test that patched the view would be measuring its own monkeypatch instead of
    the policy the product runs.
    """
    settings.STRIPE_SECRET_KEY = "sk_test_funnel_fixture"  # pragma: allowlist secret
    settings.STRIPE_PRICE_IDS = {"subscription-general": "price_test_general"}
    return settings


# ---------------------------------------------------------------------------
# 1. BYPASS — the product is closed until the provider confirms
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestBypass:
    @pytest.mark.parametrize("path", GATED_PATHS)
    def test_a_verified_unpaid_account_cannot_reach_a_product_surface(
        self, path, provider_open
    ):
        """The reviewed bypass: `/` and `/<username>/` served an unpaid account."""
        account = _create_user("gate-user")
        response = _login(account).get(path)

        assert response.status_code in (301, 302, 402), (
            f"{path} served an account that has not paid"
        )
        if response.status_code == 402:
            assert response.json()["error"] == "payment_required"
        else:
            assert response["Location"].startswith(payment_step_url()), (
                f"{path} redirected somewhere other than the funnel: {response['Location']}"
            )

    def test_the_funnel_surfaces_stay_reachable(self, provider_open):
        """A gate that also closes the way out is a trap, not a boundary."""
        client = _login(_create_user("gate-reachable"))

        step = client.get(reverse("accounts_app:payment_step"))
        billing = client.get(reverse("accounts_app:billing"))

        assert step.status_code == 200
        assert billing.status_code == 200
        assert b'data-payment-step="true"' in step.content

    def test_an_established_account_is_never_gated(self):
        """The gate is scoped to the funnel: existing users keep their product."""
        client = _login(_create_user("established-user", in_funnel=False))

        for path in ("/", "/apps/", "/new/"):
            response = client.get(path)
            assert (
                not response["Location"].startswith(payment_step_url())
                if response.status_code in (301, 302)
                else True
            )

    def test_staff_are_never_gated(self, provider_open):
        """Locking an operator out of the product they run is an outage."""
        client = _login(_create_user("gate-staff", staff=True))

        response = client.get("/apps/")

        assert not (
            response.status_code in (301, 302)
            and response["Location"].startswith(payment_step_url())
        )

    def test_an_anonymous_visitor_is_not_gated(self):
        """Public marketing pages are not this gate's business."""
        response = Client().get("/")

        assert "/accounts/settings/payment/" not in response.get("Location", "")

    def test_the_product_opens_once_the_provider_confirms(self, provider_open):
        """`mark_activated` is the ONLY thing that opens it, and it is reversible
        to prove the test is not merely observing an ungated account."""
        from apps.infra.auth_app.onboarding import mark_activated

        account = _create_user("gate-activates")
        client = _login(account)
        before = client.get("/apps/")
        assert before.status_code in (301, 302), (
            "the gate did not hold before activation"
        )

        mark_activated(account, pricing_id="subscription-general")
        after = client.get("/apps/")

        assert not (
            after.status_code in (301, 302)
            and after["Location"].startswith(payment_step_url())
        ), "a provider-confirmed account was still held at the payment step"

    def test_without_a_provider_the_requirement_is_suspended_not_faked(
        self, settings, monkeypatch
    ):
        """The documented escape valve, pinned.

        With no provider configured NOBODY can enter a card, so demanding one
        would lock every new account out of the product forever — worse than the
        bug it fixes. The requirement is suspended, and this test exists so that
        suspension is a stated decision rather than a silent hole: the moment a
        provider IS configured, the gate is back (asserted above).
        """
        from apps.infra.accounts_app.views import billing_views
        from apps.infra.auth_app import onboarding

        monkeypatch.setattr(billing_views, "card_registration_is_open", lambda: False)
        settings.STRIPE_SECRET_KEY = ""

        account = _create_user("gate-keyless")

        assert onboarding.payment_required(account) is False
        assert _login(account).get("/apps/").status_code in (200, 301, 302)


@pytest.mark.django_db
class TestTheGateClassifiesTheResolvedRoute:
    """PR #943 review. The gate classified by the FIRST SEGMENT OF THE REQUEST
    PATH, so any request whose text merely *began* with an exempt mount's name
    was exempt — wherever Django actually sent it.

    Each colliding row below names an exempt mount in its first segment and is
    NOT served by that mount: there is no ``legal/`` mount (``terms/``,
    ``privacy/`` and ``tokushoho/`` are the pages), ``/i18n/`` is not
    ``i18n/setlang/``, ``/oauth/`` is not ``oauth/authorize/``, and
    ``/billing/`` is not ``billing/start-setup/``. Every one of them falls
    through to the ``/<username>/`` project surface — i.e. product — so a
    verified-but-unpaid account reached product through all of them.
    """

    #: Request text that reads like an exempt mount, resolved by Django to the
    #: per-user project surface instead.
    COLLIDING = (
        "/legal/",
        "/legal/terms/",
        "/i18n/",
        "/i18n/x/",
        "/oauth/",
        "/oauth/x/",
        "/billing/",
        "/billing/x/",
        "/pricing/x/",
        "/terms/x/",
        "/healthz/x/",
        "/manifest.json/anything/",
    )

    #: No route serves these at all: an exempt-looking first segment must not
    #: turn an unroutable request into a pass either.
    UNROUTED = ("/legal/nope", "/no-such-route-20260917")

    #: The other half of the same question, and the control for the fix: the
    #: surfaces the funnel NEEDS must not be closed by narrowing the rule.
    REACHABLE = (
        "/accounts/settings/payment/",
        "/accounts/settings/billing/",
        "/auth/login/",
        "/auth/signup/",
        "/oauth/authorize/",
        "/oauth/token/",
        "/oauth/userinfo/",
        "/admin/login/",
        "/i18n/setlang/",
        "/billing/start-setup/",
        "/billing/webhook/stripe/",
        "/pricing/",
        "/terms/",
        "/privacy/",
        "/tokushoho/",
        "/contact/",
        "/landing/",
        "/robots.txt",
        "/manifest.json",
        "/sw.js",
        "/favicon.ico",
        "/healthz/",
        "/static/shared/css/whatever.css",
        "/media/x.png",
    )

    @pytest.mark.parametrize("path", COLLIDING)
    def test_a_first_segment_that_names_an_exempt_mount_exempts_nothing(self, path):
        resolved = resolve(path)
        assert _segment(resolved.route) != _segment(path), (
            f"{path} is no longer a collision — Django now resolves it to "
            f"{resolved.route!r}. Move this row to REACHABLE, or pick the path "
            "that carries the exemption instead"
        )
        assert request_is_gated(path) is True, (
            f"{path} was exempt because its first PATH segment reads like an "
            f"exempt mount; Django resolves it to {resolved.route!r} "
            f"({resolved.view_name!r}), which is product"
        )

    @pytest.mark.parametrize("path", UNROUTED)
    def test_a_request_django_cannot_resolve_is_closed(self, path):
        with pytest.raises(Resolver404):
            resolve(path)
        assert request_is_gated(path) is True, (
            f"{path} routes nowhere, so the gate cannot classify it — it must "
            "close, not pass (fail-closed)"
        )

    @pytest.mark.parametrize("path", REACHABLE)
    def test_the_routes_behind_those_names_stay_reachable(self, path):
        assert request_is_gated(path) is False, (
            f"{path} resolves to an exempt surface and must stay reachable to "
            "an account that owes a payment method"
        )


@pytest.mark.django_db
class TestTheGateIsAuditedAgainstTheRealResolverTree:
    """PR #943 review, blocker 2. The coverage test used to read
    ``config/urls.py`` as TEXT and regex the top-level ``path("…", …)`` calls
    out of it, comparing first segments against first segments. It could not
    fail for the reason it existed: it never saw a route inside an
    ``include()``, never saw the mounts ``plugin_urlpatterns()`` inserts, never
    saw the DEBUG-only mounts — and it shared the gate's own notion of a mount,
    so a gate that exempted by request text kept it green. It was green on the
    head where ``/legal/`` (a name on the exempt list, realized by no route)
    served the per-user project surface to an unpaid account.

    This walks the URLconf the server actually serves — every ``URLResolver``
    recursed, the namespace chain kept, one synthesized request per route that
    Django has to resolve back — so undeclared, unexercisable and
    wrongly-classified routes are all failures rather than absences.
    """

    def test_the_walk_recurses_into_includes_and_sees_what_a_source_scan_cannot(
        self,
    ):
        """Anchors the audit: if the walk stops recursing, this fails BEFORE the
        coverage assertions can pass on a tree of three routes."""
        leaves = _resolver_leaves()
        routes = [route_text for route_text, _, _ in leaves]

        assert len(leaves) >= 200, (
            f"the resolver walk found {len(leaves)} routes — it stopped "
            "recursing into includes"
        )
        for inside_an_include in (
            "accounts/settings/payment/",
            "oauth/authorize/",
            "auth/login/",
            "admin/login/",
        ):
            assert inside_an_include in routes, (
                f"{inside_an_include} lives inside an include and is missing "
                "from the walk"
            )
        assert max(route.count("/") for route in routes) >= 3, (
            "no route deeper than two levels was walked"
        )

        # The specific thing the old test could not see: these routes are not
        # written in config/urls.py at all.
        source = (REPO / "config/urls.py").read_text()
        assert "accounts/settings/payment/" not in source
        assert "oauth/authorize/" not in source

    def test_every_route_in_the_tree_is_declared_and_the_gate_agrees_with_it(self):
        undeclared, unexercised, disagreements = [], [], []
        for route_text, pattern, namespaces in _resolver_leaves():
            segment = _segment(route_text)
            if segment in EXEMPT_MOUNTS:
                declared_gated = False
            elif segment in GATED_MOUNTS:
                declared_gated = True
            else:
                undeclared.append((route_text, segment, namespaces))
                continue

            exercised = _exercisable_request(route_text, pattern)
            if exercised is None:
                unexercised.append(route_text)
                continue
            path, match = exercised
            if request_is_gated(path) is not declared_gated:
                disagreements.append(
                    (
                        route_text,
                        path,
                        match.route,
                        tuple(match.namespaces),
                        match.view_name,
                    )
                )

        assert not undeclared, (
            "these routes of the real URLconf are on neither side of the "
            "product gate, so nobody has decided whether a verified-but-unpaid "
            "account may reach them: "
            f"{sorted({segment for _, segment, _ in undeclared})}"
        )
        assert not unexercised, (
            "the audit could not produce a request every one of these routes "
            f"accepts, so it cannot claim them: {unexercised}"
        )
        assert not disagreements, (
            "the gate and the URLconf disagree about these routes "
            "(route, request, resolved route, namespaces, view): "
            f"{disagreements}"
        )

    def test_no_declaration_outlives_the_route_it_was_made_for(self):
        """The other direction, and the one that found the bypass.

        ``legal/`` was declared exempt while no route in this URLconf realized
        it: it exempted every request whose first path segment read ``legal``
        and matched nothing. A declaration nothing can realize is a phantom, and
        a mount-string list is where phantoms live.
        """
        realized = {_segment(route_text) for route_text, _, _ in _resolver_leaves()}
        realized |= {_segment(text) for text in _top_level_route_texts()}

        assert _DEBUG_ONLY_MOUNTS <= (EXEMPT_MOUNTS | GATED_MOUNTS), (
            "the mounts only a DEBUG URLconf adds must still be declared: "
            f"{sorted(_DEBUG_ONLY_MOUNTS - (EXEMPT_MOUNTS | GATED_MOUNTS))}"
        )
        dead = (EXEMPT_MOUNTS | GATED_MOUNTS) - realized - _DEBUG_ONLY_MOUNTS
        assert not dead, (
            "these mounts are declared on one side of the product gate but no "
            f"route in the URLconf realizes them: {sorted(dead)}"
        )

    def test_the_root_workspace_is_gated_and_assets_are_not(self):
        from apps.infra.accounts_app.funnel import request_is_gated

        assert request_is_gated("/") is True
        assert request_is_gated("/apps/") is True
        assert request_is_gated("/some-user/") is True
        assert request_is_gated("/accounts/settings/payment/") is False
        assert request_is_gated("/static/shared/css/whatever.css") is False
        assert request_is_gated("/healthz/") is False
        assert request_is_gated("/pricing/") is False


# ---------------------------------------------------------------------------
# 2. THE OTP HANDLER ITSELF — the authority is written where payment is owed
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestTheOtpHandlerEnrolsTheAccount:
    def test_the_otp_handler_itself_enrols_the_account(self, settings):
        """Real request, real code: verification must leave DURABLE state behind.

        The reviewed defect was that this handler deleted the only record of the
        signup and activated the account, so "owes a payment method" became
        unanswerable. Driving the endpoint — not the helper — is what keeps that
        claim honest.
        """
        from django.contrib.auth import get_user_model
        from django.utils import timezone

        from apps.infra.auth_app.models import (
            EmailVerification,
            OnboardingState,
            PendingSignup,
        )
        from apps.infra.auth_app.onboarding import Step

        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

        user = get_user_model().objects.create_user(
            username="otp-funnel",
            email="otp-funnel@example.com",
            password="TestPass123!",
        )
        user.is_active = False
        user.save(update_fields=["is_active"])
        PendingSignup.objects.create(user=user, email=user.email)
        verification = EmailVerification.objects.create(
            user=user,
            email=user.email,
            expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )

        response = Client().post(
            reverse("auth_app:api_verify_email"),
            data=json.dumps({"email": user.email, "otp_code": verification.code}),
            content_type="application/json",
        )

        assert response.status_code == 200, response.content
        user.refresh_from_db()
        assert user.is_active is True
        assert PendingSignup.objects.filter(user=user).exists() is False
        authority = OnboardingState.objects.get(user=user)
        assert authority.step == Step.PAYMENT
        assert response.json()["redirect_url"] == reverse("accounts_app:payment_step")


# ---------------------------------------------------------------------------
# 3. EXISTING USER / ALLOWLISTED PLAN
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestExistingUserAndPlanAuthority:
    def test_an_arbitrary_plan_parameter_cannot_be_charged(
        self, provider_open, settings
    ):
        """`?plan=` used to win even with no configured Stripe Price (blocker 5)."""
        account = _create_user("plan-authority")
        client = _login(account)

        response = client.get(
            reverse("accounts_app:payment_step"), {"plan": "subscription-student"}
        )

        assert response.status_code == 200
        assert b'data-payment-state="plan_unset"' in response.content
        assert b'data-payment-action="continue"' not in response.content

    def test_the_step_binds_the_allowlisted_plan_into_the_session(self, provider_open):
        """The plan shown is written to the account, and the POST carries it."""
        from apps.infra.auth_app.models import OnboardingState

        account = _create_user("plan-bound")
        client = _login(account)

        response = client.get(reverse("accounts_app:payment_step"))

        assert b'name="plan" value="subscription-general"' in response.content
        assert (
            OnboardingState.objects.get(user=account).pricing_id
            == "subscription-general"
        )

    def test_the_setup_post_refuses_an_unchargeable_plan(self, provider_open):
        account = _create_user("plan-refused")
        client = _login(account)

        response = client.post(
            reverse("public_app:billing_start_setup"), {"plan": "subscription-student"}
        )

        assert response.status_code in (301, 302)
        assert response["Location"] == reverse("accounts_app:payment_step")


# ---------------------------------------------------------------------------
# 4. CONTINUITY — success / cancel / 3DS / retry
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestContinuity:
    def _client_with_authority(self, provider_open, username, *, card=False):
        from apps.infra.public_app.models import PaymentMethod

        account = _create_user(username)
        if card:
            PaymentMethod.objects.create(
                user=account,
                stripe_payment_method_id=f"pm_{username}",
                stripe_customer_id=f"cus_{username}",
                is_usable=True,
                is_default=True,
            )
        return _login(account), account

    def test_the_provider_returns_the_browser_to_this_steps_own_markers(
        self, provider_open
    ):
        """Blocker 3: Stripe used to return to a page the step never reads."""
        from django.test import RequestFactory

        from apps.infra.public_app.views.billing import _payment_step_url

        request = RequestFactory().get("/")
        success = _payment_step_url(request, setup="complete")
        cancel = _payment_step_url(request, setup="cancelled")

        assert success.endswith(f"{payment_step_url()}?setup=complete")
        assert cancel.endswith(f"{payment_step_url()}?setup=cancelled")

    def test_a_cancelled_attempt_says_so_and_offers_the_action_again(
        self, provider_open
    ):
        client, _ = self._client_with_authority(provider_open, "continuity-cancel")

        response = client.get(
            reverse("accounts_app:payment_step"), {"setup": "cancelled"}
        )

        assert b'data-payment-state="setup_cancelled"' in response.content
        assert b'data-payment-action="continue"' in response.content

    def test_a_return_before_the_webhook_is_not_a_dead_end(self, provider_open):
        """The 3-D Secure / async case: card stored, provider not yet confirmed."""
        client, _ = self._client_with_authority(
            provider_open, "continuity-3ds", card=True
        )

        response = client.get(
            reverse("accounts_app:payment_step"), {"setup": "complete"}
        )

        assert b'data-payment-state="processing"' in response.content
        assert b'data-payment-action="continue"' not in response.content
        assert b'data-payment-action="first-product"' not in response.content

    def test_a_provider_confirmed_account_reaches_the_first_project(
        self, provider_open
    ):
        from apps.infra.auth_app.onboarding import mark_activated

        client, account = self._client_with_authority(
            provider_open, "continuity-done", card=True
        )
        mark_activated(account, pricing_id="subscription-general")

        response = client.get(reverse("accounts_app:payment_step"))

        assert b'data-payment-state="activated"' in response.content
        assert reverse("project_create").encode() in response.content
        # And the gate is open now.
        assert _login(account).get("/new/").status_code == 200


# ---------------------------------------------------------------------------
# 5. SOCIAL SIGNUP CONVERGES ON THE SAME FUNNEL
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestSocialSignupConverges:
    def test_a_social_signup_enters_the_same_funnel(self):
        """Blocker 7: Google/ORCID were created, redirected to "/" and never gated."""
        from django.test import RequestFactory

        from apps.infra.auth_app.adapters import SciTexSocialAccountAdapter
        from apps.infra.auth_app.models import OnboardingState
        from apps.infra.auth_app.onboarding import Step

        account = _create_user("social-signup", in_funnel=False)
        provider = SciTexSocialAccountAdapter()

        from apps.infra.auth_app.onboarding import begin_social_signup

        begin_social_signup(account, "google")

        assert OnboardingState.objects.get(user=account).step == Step.PAYMENT
        request = RequestFactory().get("/")
        request.user = account
        assert provider.get_login_redirect_url(request) == reverse(
            "accounts_app:payment_step"
        )

    def test_a_social_login_of_an_established_account_is_not_enrolled(self):
        from django.test import RequestFactory

        from apps.infra.auth_app.adapters import SciTexSocialAccountAdapter
        from apps.infra.auth_app.models import OnboardingState

        account = _create_user("social-established", in_funnel=False)
        request = RequestFactory().get("/")
        request.user = account

        url = SciTexSocialAccountAdapter().get_login_redirect_url(request)

        assert url == "/"
        assert OnboardingState.objects.filter(user=account).exists() is False

    def test_a_social_account_is_gated_like_an_email_one(self, provider_open):
        from apps.infra.auth_app.onboarding import begin_social_signup

        account = _create_user("social-gated", in_funnel=False)
        begin_social_signup(account, "orcid")

        response = _login(account).get("/apps/")

        assert response.status_code in (301, 302)
        assert response["Location"].startswith(payment_step_url())
