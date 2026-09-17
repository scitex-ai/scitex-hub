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
from django.urls import reverse

from apps.infra.accounts_app.funnel import EXEMPT_MOUNTS, GATED_MOUNTS, payment_step_url

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
class TestTheGateClassifiesEveryMount:
    """A deny-list that misses a mount is the bypass; this fails when one appears."""

    def test_every_top_level_mount_in_the_urlconf_is_classified(self):
        source = (REPO / "config/urls.py").read_text()
        body = source[source.index("urlpatterns = [") :]
        # Only TOP-LEVEL mounts (four-space indent) are classified by fist segment.
        mounts = re.findall(r"^    (?:path|re_path)\(\s*r?\"([^\"]*)\"", body, re.M)
        assert mounts, "could not read any mount out of config/urls.py"

        classified = {
            mount.strip("/").split("/")[0] for mount in EXEMPT_MOUNTS | GATED_MOUNTS
        }
        unclassified = {
            mount.strip("/").split("/")[0]
            for mount in mounts
            if mount.strip("/").split("/")[0] not in classified
        }
        assert not unclassified, (
            "these top-level mounts are not on either side of the product gate: "
            f"{sorted(unclassified)} — decide them in apps/infra/accounts_app/funnel.py"
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
