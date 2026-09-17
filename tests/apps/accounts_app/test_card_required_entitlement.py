#!/usr/bin/env python3
"""Card-required onboarding, enforced SERVER-SIDE (card ...entitlement-gate-20260917).

PR #934 made the payment step a real step but not a boundary: a verified user with no
usable card could still navigate straight into app routes. This is the gate.

The contract, decided with the operator:

* a verified user WITHOUT a usable, webhook-confirmed card cannot enter normal app
  routes: they go to the payment step;
* ONLY these are reachable: billing, the payment step itself, auth (login/logout/OTP),
  legal/support, and the Stripe return + webhook routes. Anything not named is GATED -
  the allowlist is closed, so a route added later is protected by default;
* entitlement is the SAME fact the rest of the hub uses:
  ``payment_methods.filter(is_usable=True, is_default=True)`` - and ``is_usable`` is
  only ever flipped by the SIGNED ``checkout.session.completed`` webhook, so nothing a
  browser can do grants it;
* staff are exempt, so an operator can still work on a locked-down deployment;
* the gate is server-side: no client redirect may substitute for it.

Two layers again: the decision is a pure function of (path, user facts) and runs with no
database; the middleware behaviour on real routes is database-gated for CI.
"""

from __future__ import annotations

import pytest

from apps.infra.accounts_app.entitlement import (
    GATED,
    OPEN,
    card_required_decision,
    path_is_reachable_without_card,
)

PAYMENT_STEP = "/accounts/settings/payment/"


# ---------------------------------------------------------------------------
# the closed allowlist (pure)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        # the step itself, or the redirect loops forever
        PAYMENT_STEP,
        # billing, in every form the funnel uses
        "/accounts/settings/billing/",
        "/billing/start-setup/",
        "/billing/checkout/",
        "/billing/return/",
        "/billing/portal/",
        # Stripe's own callbacks: the webhook is how entitlement is GRANTED, so it can
        # never sit behind the gate it feeds
        "/billing/webhook/stripe/",
        # auth: login, logout, signup, OTP, password reset, social return
        "/auth/login/",
        "/auth/signin/",
        "/auth/logout/",
        "/auth/signup/",
        "/auth/verify-email/",
        "/auth/reset-password/",
        "/accounts/oauth/google/login/callback/",
        # legal + support + contact
        "/legal/terms/",
        "/terms/",
        "/privacy/",
        "/cookies/",
        "/support/",
        "/contact/",
        # infrastructure the page cannot work without
        "/static/shared/css/common.css",
        "/media/logo.png",
        "/favicon.ico",
        "/healthz",
    ],
)
def test_these_routes_are_reachable_without_a_card(path):
    assert path_is_reachable_without_card(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/apps/",
        "/apps/agents/",
        "/apps/cards/",
        "/apps/stats/",
        "/apps/writer/",
        "/apps/my-projects/",
        "/chat/",
        "/console/",
        "/accounts/settings/",
        "/accounts/profile/",
    ],
)
def test_everything_else_is_gated_by_default(path):
    """Including "/" and the launcher: the funnel is account -> OTP -> card -> app."""
    assert path_is_reachable_without_card(path) is False


def test_the_allowlist_is_closed_not_open():
    """A route nobody has thought about yet must be GATED - that is the point of the
    list being an allowlist. If this ever fails, the gate has been inverted."""
    for invented in ("/apps/brand-new-app-2030/", "/workspace/", "/api/internal/x/"):
        assert path_is_reachable_without_card(invented) is False


def test_a_lookalike_prefix_does_not_sneak_in():
    """`/auth-by-accident/` must not match the `/auth/` prefix, and neither may
    `/accounts/settings/billing-questions/`."""
    for lookalike in ("/authz/", "/authbypass/", "/legalish/", "/support-me/"):
        assert path_is_reachable_without_card(lookalike) is False


def test_the_real_webhook_route_is_pinned_to_the_urlconf():
    """Written after getting it wrong: I asserted a made-up
    /apps/public_app/billing/webhook/stripe/ and it does not exist.

    The webhook is the route that GRANTS entitlement, so a stale path here would either
    gate the grant or leave it exposed. Derive it from the URLconf instead of retyping
    it, so a move breaks this test rather than the fence.
    """
    from django.urls import reverse

    webhook = reverse("public_app:stripe_webhook")

    assert path_is_reachable_without_card(webhook) is True
    assert webhook == "/billing/webhook/stripe/"


def test_the_payment_step_is_the_only_redirect_target_and_is_itself_reachable():
    """A redirect target that is not on the allowlist loops forever.

    DEPENDENCY, stated rather than skipped silently: the route
    ``accounts_app:payment_step`` ships with PR #934, which is not merged yet. This gate
    therefore redirects to the LITERAL path (which is on the allowlist and which #934
    serves), and this test asserts the two agree the moment the route exists. Until then
    it is marked xfail(strict=False) so the day #934 lands, an XPASS tells us to make it
    a hard assertion.
    """
    from django.urls import NoReverseMatch, reverse

    from apps.infra.accounts_app.entitlement import PAYMENT_STEP_PATH

    assert path_is_reachable_without_card(PAYMENT_STEP_PATH) is True
    try:
        resolved = reverse("accounts_app:payment_step")
    except NoReverseMatch:
        pytest.xfail("accounts_app:payment_step arrives with PR #934; literal path is used")
    assert resolved == PAYMENT_STEP_PATH


# ---------------------------------------------------------------------------
# the decision (pure) - who is gated
# ---------------------------------------------------------------------------


class _User:
    """A stub with only the facts the decision may use."""

    def __init__(self, *, authenticated=True, staff=False, usable_card=False):
        self.is_authenticated = authenticated
        self.is_staff = staff
        self.is_superuser = False
        self._usable = usable_card

    @property
    def payment_methods(self):
        usable = self._usable

        class _QS:
            def filter(self, **_kw):
                return self

            def exists(self):
                return usable

        return _QS()


def test_a_verified_user_without_a_usable_card_is_sent_to_the_payment_step():
    decision, target = card_required_decision("/apps/agents/", _User())

    assert decision == GATED
    assert target == PAYMENT_STEP


def test_a_user_with_a_webhook_confirmed_card_passes():
    decision, _target = card_required_decision("/apps/agents/", _User(usable_card=True))

    assert decision == OPEN


def test_an_anonymous_request_is_not_gated():
    """Sign-in is the auth layer's job; sending an anonymous visitor to the PAYMENT
    step would ask for a card before an account exists."""
    decision, _target = card_required_decision("/apps/agents/", _User(authenticated=False))

    assert decision == OPEN


def test_staff_are_exempt():
    """Otherwise an operator cannot open anything on a locked-down deployment - and the
    person who most needs to see the funnel is the one who cannot pass it."""
    decision, _target = card_required_decision("/apps/agents/", _User(staff=True))

    assert decision == OPEN


def test_an_allowlisted_route_is_open_even_without_a_card():
    decision, _target = card_required_decision("/accounts/settings/billing/", _User())

    assert decision == OPEN


def test_a_cardless_user_is_never_redirected_to_the_route_they_asked_for():
    """The loop guard: if the target ever equals the request path, the browser bounces
    forever between the two."""
    for path in ("/apps/agents/", "/chat/", "/", "/apps/my-projects/"):
        decision, target = card_required_decision(path, _User())
        if decision == GATED:
            assert target != path


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))


# ---------------------------------------------------------------------------
# the wall itself, on real routes (CI - needs a database)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTheWallOnRealRoutes:
    """The middleware, driven through the Django test client.

    Each case names the routing fact it depends on, because a route that moves silently
    changes what the wall protects.
    """

    def _payment_step(self):
        from django.urls import reverse

        return reverse("accounts_app:payment_step")

    def _cardless(self, username="wall-cardless"):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_user(
            username=username, email=f"{username}@example.com", password="TestPass123!"
        )

    def _with_card(self, username="wall-carded"):
        from apps.infra.public_app.billing_models import PaymentMethod

        user = self._cardless(username)
        PaymentMethod.objects.create(
            user=user, is_usable=True, is_default=True,
            stripe_payment_method_id="pm_test_wall", brand="visa", last4="4242",
        )
        return user

    def test_an_app_route_sends_a_cardless_user_to_the_payment_step(self, client):
        client.force_login(self._cardless())

        response = client.get("/apps/agents/")

        assert response.status_code == 302
        assert response["Location"] == self._payment_step()

    def test_the_same_route_opens_for_a_user_with_a_usable_card(self, client):
        client.force_login(self._with_card())

        response = client.get("/apps/agents/")

        assert response.status_code not in (301, 302), "a carded user must not be gated"

    def test_the_payment_step_itself_never_redirects_to_itself(self, client):
        client.force_login(self._cardless())

        response = client.get(self._payment_step())

        assert response.status_code == 200, "the gate must not loop on its own target"

    def test_billing_stays_reachable_without_a_card(self, client):
        client.force_login(self._cardless())

        response = client.get("/accounts/settings/billing/")

        assert response.status_code == 200

    def test_the_stripe_webhook_is_never_behind_the_gate_it_grants(self, client):
        """The webhook is how a card BECOMES usable; gating it would deadlock the
        funnel for everyone, forever."""
        from django.urls import reverse

        response = client.post(reverse("public_app:stripe_webhook"), data="{}", content_type="application/json")

        assert not (response.status_code == 302 and response.get("Location") == self._payment_step()), (
            "the webhook was redirected to the payment step"
        )

    def test_an_unusable_or_non_default_card_does_not_grant_entry(self, client):
        """The point of the gate: a card row is not entitlement. Only the webhook's
        is_usable AND is_default pair is."""
        from apps.infra.public_app.billing_models import PaymentMethod

        user = self._cardless("wall-not-usable")
        PaymentMethod.objects.create(
            user=user, is_usable=False, is_default=True,
            stripe_payment_method_id="pm_test_incomplete", brand="visa", last4="4242",
        )
        client.force_login(user)

        response = client.get("/apps/agents/")

        assert response.status_code == 302
        assert response["Location"] == self._payment_step()

    def test_staff_are_not_walled_out(self, client):
        from django.contrib.auth import get_user_model

        staff = get_user_model().objects.create_user(
            username="wall-staff", email="wall-staff@example.com", password="TestPass123!",
            is_staff=True,
        )
        client.force_login(staff)

        response = client.get("/apps/agents/")

        assert response.status_code not in (301, 302)
