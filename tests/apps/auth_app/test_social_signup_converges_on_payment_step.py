#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A new SOCIAL account joins the same funnel step as a verified email signup.

THE GAP, measured on the running code. The email path is OTP-first: signup
creates an INACTIVE row, the six-digit code verifies it, and the verification
endpoint then publishes the next step with ``post_signup_redirect_url(user)``
(``apps/infra/auth_app/api_views.py``). Card-required onboarding means that next
step is the payment step, not the app.

The social path published nothing of the sort. A brand-new Google/ORCID signup
went through allauth's own signup redirect, which is
``ACCOUNT_SIGNUP_REDIRECT_URL`` — "/" — so a user who arrived through Google
never saw the step their card and trial terms live on, while the account they
had just created was in exactly the same state as an OTP-verified one.

WHAT MAKES THEM CONVERGE, and why it is not a copy of the URL. The social hook
calls the SAME function the email path calls — ``post_signup_redirect_url`` —
rather than repeating the route it currently returns. One source, two callers:
the targets cannot drift apart, and the payment step can move (it is moving in
PR #934, from billing to a dedicated step) without this file changing. The tests
assert equality WITH THAT FUNCTION, not with a literal, so a future change to
the funnel target keeps them honest instead of silently pinning "/".

EXISTING ACCOUNTS ARE UNTOUCHED. Only SIGNUP is redirected; an existing user
signing in with Google/ORCID keeps the ordinary login target, which is the
behaviour this branch must not disturb — ``TestExistingAccountLoginIsUnchanged``
asserts it through allauth's own login flow, and it is the reason the hook is
``get_signup_redirect_url`` (allauth calls it with ``signup=True``) rather than
the login redirect.

OTP-FIRST EMAIL SIGNUP IS UNTOUCHED TOO, and pinned here rather than assumed:
``TestTheEmailPathIsStillOtpFirst`` posts a real signup and asserts the visitor
lands on the verification step, not on the payment step, and is not signed in.

No mocks (project rule): the real allauth flows, the real adapter, the real
signup view.
"""

import pytest
from allauth.core import context as allauth_context
from allauth.socialaccount.internal.flows.login import _login as login_existing_account
from allauth.socialaccount.internal.flows.signup import complete_social_signup
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.shortcuts import resolve_url
from django.test import RequestFactory
from django.urls import reverse

from apps.infra.auth_app.forms import SignupForm
from apps.infra.public_app.services.billing_provider import post_signup_redirect_url

User = get_user_model()

SIGNUP_URL = "/auth/signup/"

#: allauth's own default for a completed signup, read by the same code path when
#: this hook is absent. A recognised marker, so "the social signup went to the
#: funnel step" cannot be satisfied by falling through to allauth's default.
ALLAUTH_DEFAULT_SIGNUP_TARGET = "/allauth-default-signup-target/"

_PASSWORD = "Gx7-quiet-harbour-42"


def _request(path="/"):
    """A request with the middleware a real signup/login response goes through."""
    request = RequestFactory().get(path)
    SessionMiddleware(lambda r: None).process_request(request)
    MessageMiddleware(lambda r: None).process_request(request)
    AuthenticationMiddleware(lambda r: None).process_request(request)
    return request


@pytest.fixture
def fresh_social_signup(db):
    """Drive allauth's real new-account signup flow and return (response, user)."""
    from allauth.socialaccount.models import SocialLogin

    def _run(provider="google", next_url=None):
        user = User.objects.create_user(
            username=f"{provider}_newcomer",
            email=f"{provider}_newcomer@example.com",
            password=None,
        )
        sociallogin = SocialLogin(
            user=user,
            account=SocialAccount(provider=provider, uid=f"{provider}-uid-new"),
        )
        sociallogin.state = {"next": next_url} if next_url else {}
        sociallogin._did_authenticate_by_email = None
        request = _request()
        # allauth's own middleware wraps every request in this context; the flow
        # function is being driven directly here, so it is entered explicitly
        # rather than stubbed.
        with allauth_context.request_context(request):
            response = complete_social_signup(request, sociallogin)
        return response, user

    return _run


@pytest.fixture
def existing_social_account(db):
    """An account that already exists and is signing in again with its provider."""
    from allauth.socialaccount.models import SocialLogin

    user = User.objects.create_user(
        username="google_returning",
        email="google_returning@example.com",
        password=None,
    )
    account = SocialAccount.objects.create(user=user, provider="google", uid="google-uid-existing")
    sociallogin = SocialLogin(user=user, account=account)
    sociallogin.state = {}
    sociallogin._did_authenticate_by_email = None
    return sociallogin, user


def _login_via_allauth(sociallogin):
    """Sign an EXISTING account in through allauth's own login flow."""
    request = _request()
    with allauth_context.request_context(request):
        response = login_existing_account(request, sociallogin)
    return request, response


@pytest.mark.auth
class TestANewSocialAccountLandsOnTheFunnelStep:
    """The social signup publishes the same next step the OTP path publishes."""

    @pytest.mark.django_db
    def test_the_new_signup_is_redirected_to_the_published_funnel_step(self, fresh_social_signup):
        # Arrange
        response, user = fresh_social_signup("google")
        # Act
        target = response["Location"]
        # Assert
        assert target == post_signup_redirect_url(user)

    @pytest.mark.django_db
    def test_the_orcid_signup_lands_there_too(self, fresh_social_signup):
        # Arrange
        response, user = fresh_social_signup("orcid")
        # Act
        target = response["Location"]
        # Assert
        assert target == post_signup_redirect_url(user)

    @pytest.mark.django_db
    def test_the_target_is_not_allauths_own_signup_default(self, fresh_social_signup, settings):
        # The defect was precisely that the social flow fell through to
        # ACCOUNT_SIGNUP_REDIRECT_URL. Made deterministic: point that setting
        # somewhere recognisable and require the response to ignore it.
        # Arrange
        settings.ACCOUNT_SIGNUP_REDIRECT_URL = ALLAUTH_DEFAULT_SIGNUP_TARGET
        # Act
        response, _user = fresh_social_signup("google")
        target = response["Location"]
        # Assert
        assert target != ALLAUTH_DEFAULT_SIGNUP_TARGET

    @pytest.mark.django_db
    def test_the_funnel_step_carries_no_next_parameter_to_bypass_it(self, fresh_social_signup):
        # A "next" the visitor controls would let the payment step be skipped;
        # none is present, so the target is the funnel's decision end to end.
        # Arrange
        response, _user = fresh_social_signup("google")
        # Act
        location = response["Location"]
        # Assert
        assert "next=" not in location


@pytest.mark.auth
class TestExistingAccountLoginIsUnchanged:
    """Only SIGNUP converges. A returning user keeps the ordinary target."""

    @pytest.mark.django_db
    def test_an_existing_account_keeps_the_login_target(self, existing_social_account, settings):
        # Arrange
        sociallogin, _user = existing_social_account
        # Act
        _request_obj, response = _login_via_allauth(sociallogin)
        # Assert
        assert response["Location"] == resolve_url(settings.LOGIN_REDIRECT_URL)

    @pytest.mark.django_db
    def test_an_existing_account_is_not_pushed_at_the_funnel_step(self, existing_social_account):
        # Arrange
        sociallogin, user = existing_social_account
        # Act
        _request_obj, response = _login_via_allauth(sociallogin)
        # Assert
        assert response["Location"] != post_signup_redirect_url(user)

    @pytest.mark.django_db
    def test_the_returning_user_is_really_signed_in(self, existing_social_account):
        # Arrange: the redirect above only means "signed in" if a session was made
        sociallogin, user = existing_social_account
        # Act
        request, _response = _login_via_allauth(sociallogin)
        # Assert
        assert request.user.pk == user.pk


@pytest.mark.auth
@pytest.mark.guards(
    defect=(
        "A brand-new social account carrying a local next= (for example "
        "/bypass-target/) was redirected straight there: allauth reads "
        "sociallogin.state['next'] and passes it as the explicit redirect, so "
        "get_signup_redirect_url was never consulted and the funnel step was "
        "skipped for a new account."
    )
)
class TestANewAccountCannotChooseItsOwnLanding:
    """``next`` is a hint for a returning user — never a door past onboarding.

    FOUND BY REVIEW, and it is the defect this whole class exists for: allauth
    reads the target for a brand-new social account from ``sociallogin.state["next"]``
    (``complete_social_signup`` passes ``sociallogin.get_redirect_url(request)``
    into ``perform_login``, and ``get_login_redirect_url`` returns that value
    BEFORE it ever asks ``get_signup_redirect_url``). A local ``next`` therefore
    wins outright: a real new-account Google probe carrying
    ``next=/bypass-target/`` landed on ``/bypass-target/``, past the step every
    new account is subject to. External ``next`` values never reach the state
    (``state_from_request`` validates with ``is_safe_url``), so the hole is
    LOCAL paths — which is the dangerous shape, because a local path can be any
    app route.

    The rule now: a NEW account's landing is chosen by the funnel, full stop,
    even when a next was carried. An existing account keeps the validated next,
    which is what ``next`` is for.
    """

    @pytest.mark.django_db
    @pytest.mark.parametrize("provider", ["google", "orcid"])
    def test_a_local_next_does_not_beat_the_funnel_step(self, fresh_social_signup, provider):
        # Arrange: the exact shape the review probe used
        response, user = fresh_social_signup(provider, next_url="/bypass-target/")
        # Act
        target = response["Location"]
        # Assert
        assert target == post_signup_redirect_url(user)
        assert target != "/bypass-target/"

    @pytest.mark.django_db
    def test_an_injected_external_next_does_not_beat_it_either(self, fresh_social_signup):
        # Belt and braces: if a hostile value ever reached the state by another
        # road, the funnel is still authoritative.
        # Arrange
        response, user = fresh_social_signup("google", next_url="https://bypass.example/target/")
        # Act
        target = response["Location"]
        # Assert
        assert target == post_signup_redirect_url(user)

    def test_the_state_builder_stores_no_external_next(self, settings):
        # Why the external case cannot arise through the real path — while
        # ALLOWED_HOSTS is meaningful: the state is built by state_from_request,
        # which validates with is_safe_url. Pinned here, because THIS
        # DEVELOPMENT ENVIRONMENT has "*" in ALLOWED_HOSTS (measured), which
        # makes is_safe_url accept any host at all. That is the reason the
        # refusal for a new account lives in post_login — a rule that does not
        # depend on how permissive the host allowlist happens to be.
        # Arrange
        from allauth.socialaccount.models import SocialLogin

        settings.ALLOWED_HOSTS = ["testserver"]
        request = RequestFactory().get("/?next=https://bypass.example/target/")
        # Act
        with allauth_context.request_context(request):
            state = SocialLogin.state_from_request(request)
        # Assert
        assert "next" not in state

    def test_the_state_builder_still_stores_a_local_next(self, settings):
        # The local case IS storable — which is exactly why the redirect, not the
        # state, has to be the thing that refuses for a new account.
        # Arrange
        from allauth.socialaccount.models import SocialLogin

        settings.ALLOWED_HOSTS = ["testserver"]
        request = RequestFactory().get("/?next=/bypass-target/")
        # Act
        with allauth_context.request_context(request):
            state = SocialLogin.state_from_request(request)
        # Assert
        assert state["next"] == "/bypass-target/"

    @pytest.mark.django_db
    def test_an_existing_login_still_honours_a_validated_local_next(self, existing_social_account):
        # Preservation, in the same breath as the fix: next is FOR the returning
        # user, and a new account must not take it away from them.
        # Arrange
        sociallogin, user = existing_social_account
        sociallogin.state = {"next": "/accounts/settings/"}
        # Act
        request = _request()
        with allauth_context.request_context(request):
            response = login_existing_account(request, sociallogin)
        # Assert
        assert response["Location"] == "/accounts/settings/"

    @pytest.mark.django_db
    def test_an_existing_login_without_a_next_keeps_the_ordinary_target(self, existing_social_account, settings):
        # Arrange
        sociallogin, _user = existing_social_account
        # Act
        _request_obj, response = _login_via_allauth(sociallogin)
        # Assert
        assert response["Location"] == resolve_url(settings.LOGIN_REDIRECT_URL)


@pytest.mark.auth
class TestTheEmailPathIsStillOtpFirst:
    """Preserved, not assumed: a fresh email signup still goes to the code step."""

    @pytest.mark.django_db
    def test_a_signup_is_sent_to_the_verification_step(self, client):
        # Arrange
        payload = {
            "username": "otp_first_probe",
            "email": "otp_first_probe@example.com",
            "password": _PASSWORD,
            "agree_terms": "on",
        }
        if "password2" in SignupForm().fields:
            payload["password2"] = _PASSWORD
        # Act
        response = client.post(SIGNUP_URL, payload)
        # Assert
        assert response.status_code == 302
        assert response["Location"].startswith(reverse("auth_app:verify_email"))

    @pytest.mark.django_db
    def test_a_signup_is_not_yet_told_about_the_payment_step(self, client):
        # The card step is published only AFTER the address is verified; sending
        # a fresh signup there would put a card form in front of an unverified
        # address, and would skip the OTP that proves the address exists.
        # Arrange
        payload = {
            "username": "otp_first_probe",
            "email": "otp_first_probe@example.com",
            "password": _PASSWORD,
            "agree_terms": "on",
        }
        if "password2" in SignupForm().fields:
            payload["password2"] = _PASSWORD
        # Act
        response = client.post(SIGNUP_URL, payload)
        # Assert
        assert post_signup_redirect_url(User(username="otp_first_probe")) not in response["Location"]

    @pytest.mark.django_db
    def test_the_signup_does_not_start_a_session(self, client):
        # OTP-first means the visitor is NOT signed in until the code arrives.
        # Arrange
        payload = {
            "username": "otp_first_probe",
            "email": "otp_first_probe@example.com",
            "password": _PASSWORD,
            "agree_terms": "on",
        }
        if "password2" in SignupForm().fields:
            payload["password2"] = _PASSWORD
        # Act
        client.post(SIGNUP_URL, payload)
        # Assert
        assert "_auth_user_id" not in client.session

    @pytest.mark.django_db
    def test_the_created_account_is_inactive_until_verified(self, client):
        # Arrange
        payload = {
            "username": "otp_first_probe",
            "email": "otp_first_probe@example.com",
            "password": _PASSWORD,
            "agree_terms": "on",
        }
        if "password2" in SignupForm().fields:
            payload["password2"] = _PASSWORD
        # Act
        client.post(SIGNUP_URL, payload)
        # Assert
        assert User.objects.get(username="otp_first_probe").is_active is False


@pytest.mark.auth
class TestBothPathsReadOneSource:
    """The convergence is a shared function, so the targets cannot drift."""

    def test_the_verification_endpoint_publishes_the_same_call(self):
        # The email path's publisher (auth_app/api_views.py) and this hook must
        # be the same function object: one source, two callers.
        # Arrange
        from apps.infra.auth_app import api_views

        # Act
        from_email_path = api_views.post_signup_redirect_url
        used_by_social = post_signup_redirect_url
        # Assert
        assert from_email_path is used_by_social


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
