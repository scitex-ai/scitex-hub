#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The auth pages must only offer a social provider that can actually be used.

THE DEFECT, measured on live production 2026-08-16. ``/auth/signin/`` rendered
a "Google" and an "ORCID" button, server-side, to anonymous visitors — two
clicks from the landing page (``/landing/`` -> "Sign in" -> "Google"). Both
anchors pointed at ``/auth/social/<provider>/login/`` and both returned HTTP
500, because ``signin.html`` and ``signup.html`` hardcoded the two anchors
instead of deriving them from the providers allauth can actually serve. With
zero ``SocialApp`` rows and no ``APP``/``APPS`` key in
``SOCIALACCOUNT_PROVIDERS``, allauth's
``DefaultSocialAccountAdapter.get_app`` raises ``SocialApp.DoesNotExist`` and
the request 500s. Nobody had ever completed an OAuth login on that
deployment.

WHY BOTH DIRECTIONS ARE TESTED. Hiding the buttons is only half the fix. A
template that hid them unconditionally would look identical on today's
production — zero configured apps — and would silently keep OAuth dead on the
day credentials arrive. So
``TestAConfiguredProviderStillGetsItsButton`` is the load-bearing half: it is
what distinguishes "derive the buttons from allauth's own provider list" from
"delete the feature".

No mocks (project rule): real ``SocialApp`` rows, the real URLconf, the real
templates, rendered through the real views with Django's test client.
"""

import re

import pytest
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

SIGNIN_URL = "/auth/signin/"
SIGNUP_URL = "/auth/signup/"

# ``/auth/login/`` is the same view and the same template as ``/auth/signin/``
# (apps/infra/auth_app/urls.py routes both to ``views.login_view``), so it is
# a third public door onto the identical markup.
LOGIN_URL = "/auth/login/"

GOOGLE_LOGIN_PATH = "/auth/social/google/login/"
ORCID_LOGIN_PATH = "/auth/social/orcid/login/"

DEFECT = (
    "signin.html and signup.html hardcoded Google/ORCID anchors to "
    "/auth/social/<provider>/login/, so with no usable SocialApp every "
    "anonymous visitor was two clicks from an HTTP 500."
)

_SOCIAL_HREF = re.compile(r'href="(/auth/social/[^"]*)"')


def _social_links(response):
    """Every ``/auth/social/…`` href the rendered page hands a visitor."""
    return _SOCIAL_HREF.findall(response.content.decode("utf-8"))


@pytest.fixture(params=[SIGNIN_URL, LOGIN_URL, SIGNUP_URL])
def auth_page(request):
    """Each public page that carries the social-login block."""
    return request.param


@pytest.fixture
def google_app(db):
    """A real, usable Google app — the state allauth requires to serve a login.

    This is exactly what production is missing: ``SocialApp.objects.all()`` is
    empty there, which is why ``get_app`` raises.
    """
    app = SocialApp.objects.create(
        provider="google",
        name="Google",
        client_id="test-client-id",
        secret="test-secret",
    )
    app.sites.add(Site.objects.get_current())
    return app


@pytest.fixture
def no_provider_response(client, db, auth_page):
    """The page as production serves it today: not one configured app."""
    assert not SocialApp.objects.exists()
    return client.get(auth_page)


@pytest.fixture
def no_provider_body(no_provider_response):
    return no_provider_response.content.decode("utf-8")


@pytest.fixture
def google_only_response(client, google_app, auth_page):
    """The page with Google configured and ORCID still unconfigured."""
    return client.get(auth_page)


@pytest.fixture
def google_only_body(google_only_response):
    return google_only_response.content.decode("utf-8")


@pytest.fixture
def followed_google_link(client, google_app):
    """Follow the link the sign-in page actually offers, as a visitor would."""
    offered = _social_links(client.get(SIGNIN_URL))
    return client.get(offered[0])


@pytest.mark.auth
@pytest.mark.guards(defect=DEFECT)
class TestNoUsableProviderMeansNoSocialLink:
    """With zero configured apps, the pages must offer no route into the 500."""

    def test_the_page_still_renders(self, no_provider_response):
        # Arrange: no_provider_response fetched the page with no SocialApp rows
        response = no_provider_response
        # Act
        status = response.status_code
        # Assert
        assert status == 200

    def test_no_social_link_is_offered(self, no_provider_response):
        # Arrange: no_provider_response fetched the page with no SocialApp rows
        response = no_provider_response
        # Act
        links = _social_links(response)
        # Assert
        assert links == []

    def test_the_divider_markup_goes_too(self, no_provider_body):
        # A bare separator above nothing is its own small defect.
        # Arrange: no_provider_body is the page with no SocialApp rows
        body = no_provider_body
        # Act
        present = "social-login-divider" in body
        # Assert
        assert present is False

    def test_the_continue_with_caption_goes_too(self, no_provider_body):
        # Arrange: no_provider_body is the page with no SocialApp rows
        body = no_provider_body
        # Act
        present = "or continue with" in body
        # Assert
        assert present is False

    def test_the_sign_up_with_caption_goes_too(self, no_provider_body):
        # Arrange: no_provider_body is the page with no SocialApp rows
        body = no_provider_body
        # Act
        present = "or sign up with" in body
        # Assert
        assert present is False


@pytest.mark.auth
@pytest.mark.guards(defect=DEFECT)
class TestAConfiguredProviderStillGetsItsButton:
    """The fix must be "derive from allauth", not "always hide".

    This is the more important half. Without it, a template that simply
    deleted the buttons would satisfy every assertion above and would keep
    OAuth broken forever once real credentials arrive.
    """

    def test_configured_google_link_is_offered(self, google_only_response):
        # Arrange: google_only_response has a real Google SocialApp row
        response = google_only_response
        # Act
        links = _social_links(response)
        # Assert
        assert GOOGLE_LOGIN_PATH in links

    def test_configured_google_is_labelled(self, google_only_body):
        # Arrange: google_only_body has a real Google SocialApp row
        body = google_only_body
        # Act
        present = "btn-google" in body
        # Assert
        assert present is True

    def test_the_divider_comes_back_with_it(self, google_only_body):
        # Arrange: google_only_body has a real Google SocialApp row
        body = google_only_body
        # Act
        present = "social-login-divider" in body
        # Assert
        assert present is True

    def test_unconfigured_orcid_stays_hidden_beside_it(self, google_only_response):
        # Per provider, not all-or-nothing: ORCID has no app, so its anchor is
        # still a route into the 500 and must not be rendered.
        # Arrange: google_only_response configured Google only
        response = google_only_response
        # Act
        links = _social_links(response)
        # Assert
        assert ORCID_LOGIN_PATH not in links

    def test_the_offered_link_does_not_500(self, followed_google_link):
        # The actual promise: what the sign-in page shows can be clicked.
        # Arrange: followed_google_link clicked the rendered anchor
        response = followed_google_link
        # Act
        status = response.status_code
        # Assert
        assert status != 500

    def test_the_offered_link_redirects_to_the_provider(self, followed_google_link):
        # Arrange: followed_google_link clicked the rendered anchor
        response = followed_google_link
        # Act
        status = response.status_code
        # Assert
        assert status in (301, 302)


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
