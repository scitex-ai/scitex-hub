#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A provider gets a button exactly when its CREDENTIALS say allauth can serve it.

THE INVARIANT (already guarded by ``test_social_login_buttons.py``): a button
exists exactly when clicking it can succeed — a hardcoded anchor plus no usable
``SocialApp`` was a two-click route to an HTTP 500 on production.

WHERE THIS FILE TAKES OVER. ``allauth`` builds a provider's app from TWO
sources: the ``SocialApp`` database rows, and ``settings.SOCIALACCOUNT_PROVIDERS
[provider]["APP"]``. Credentials in this deployment arrive in the ENVIRONMENT
(``SCITEX_HUB_GOOGLE_CLIENT_ID``/``_SECRET``, ``SCITEX_HUB_ORCID_CLIENT_ID``/
``_SECRET``) and reached allauth's second source only if an operator remembered
to run ``manage.py setup_social_auth`` to copy them into database rows. Until
that happened, a deployment holding real, complete credentials still rendered no
Google and no ORCID button and could not complete a social login at all. The
credential settings are therefore wired into the provider configuration
directly, and one completeness rule governs both the button and the login.

WHY INCOMPLETE CREDENTIALS CONTRIBUTE NOTHING, rather than a half-built app: an
app with an empty secret is handed to the provider happily and fails later, at
the token exchange, as a 500 — the exact shape the existing invariant forbids.
So "complete" (a usable client id AND a usable secret, and neither of them a
leftover stub) is the gate, and an incomplete pair renders no button at all.

SECRETS: the client secret is passed to allauth and never rendered. That is not
assumed here — ``TestTheClientSecretNeverReachesThePage`` asserts the exact
secret string is absent from the served HTML, so "never rendered" is a red-able
assertion and fails the day someone templates the app config into a page.

No mocks (project rule): real ``SocialApp`` rows, the real settings layer, the
real URLconf, the real templates, rendered through the real views.
"""

import re

import pytest
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

from config.social_apps import credential_is_complete, with_credential_apps

SIGNIN_URL = "/auth/signin/"
SIGNUP_URL = "/auth/signup/"

GOOGLE_LOGIN_PATH = "/auth/social/google/login/"
ORCID_LOGIN_PATH = "/auth/social/orcid/login/"

#: A secret that cannot occur in a page for any legitimate reason. If it shows
#: up, it was rendered.
CANARY_SECRET = "canary-social-secret-that-must-never-be-rendered"

#: The credential stubs operators leave behind. None of these is a credential.
STUB_VALUES = ("", "   ", "CHANGEME", "change-me", "your-client-id", "<client-id>", "TODO", "xxx")

_SOCIAL_HREF = re.compile(r'href="(/auth/social/[^"]*)"')


def _social_links(body):
    """Every ``/auth/social/…`` href the served page hands a visitor."""
    return _SOCIAL_HREF.findall(body)


@pytest.fixture
def credential_settings(settings):
    """Install credentials into the REAL provider configuration, as deployment does.

    The provider skeletons (scopes, ORCID base domain, PKCE) are copied from the
    running settings untouched; only ``APP`` is added, and only for a provider
    whose pair is complete. That is the same call the settings module makes at
    import time, so this exercises the wiring rather than a stand-in for it.
    """

    def _install(credentials):
        skeleton = {pid: dict(cfg) for pid, cfg in settings.SOCIALACCOUNT_PROVIDERS.items()}
        settings.SOCIALACCOUNT_PROVIDERS = with_credential_apps(skeleton, credentials)
        return settings.SOCIALACCOUNT_PROVIDERS

    return _install


# ---------------------------------------------------------------------------
# The completeness rule itself — pure, no Django, no database.
# ---------------------------------------------------------------------------


class TestCompletenessIsTheGate:
    """A credential pair is usable, or it contributes nothing."""

    def test_a_usable_pair_is_complete(self):
        # Arrange
        client_id, secret = "1234.apps.googleusercontent.com", CANARY_SECRET
        # Act
        complete = credential_is_complete(client_id, secret)
        # Assert
        assert complete is True

    @pytest.mark.parametrize("missing", ["client_id", "secret"])
    def test_a_pair_missing_either_half_is_incomplete(self, missing):
        # Arrange: the shape that would otherwise build a half-working app
        half = {"client_id": "1234.apps.googleusercontent.com", "secret": CANARY_SECRET, missing: ""}
        # Act
        complete = credential_is_complete(half["client_id"], half["secret"])
        # Assert
        assert complete is False

    @pytest.mark.parametrize("stub", STUB_VALUES)
    def test_a_leftover_stub_is_not_a_credential(self, stub):
        # Arrange: the operator copied the .env.example line and never filled it in
        # Act
        complete = credential_is_complete(stub, CANARY_SECRET)
        # Assert
        assert complete is False

    def test_a_complete_pair_becomes_the_providers_app(self):
        # Arrange
        credentials = {"google": ("1234.apps.googleusercontent.com", CANARY_SECRET)}
        # Act
        providers = with_credential_apps({"google": {"SCOPE": ["profile"]}}, credentials)
        # Assert
        assert providers["google"]["APP"] == {
            "name": "Google",
            "client_id": "1234.apps.googleusercontent.com",
            "secret": CANARY_SECRET,
        }

    def test_an_incomplete_pair_adds_no_app_key_at_all(self):
        # Arrange
        credentials = {"google": ("1234.apps.googleusercontent.com", "")}
        # Act
        providers = with_credential_apps({"google": {"SCOPE": ["profile"]}}, credentials)
        # Assert
        assert "APP" not in providers["google"]

    def test_the_existing_provider_configuration_is_preserved(self):
        # Arrange
        credentials = {"google": ("1234.apps.googleusercontent.com", CANARY_SECRET)}
        skeleton = {"google": {"SCOPE": ["profile"], "OAUTH_PKCE_ENABLED": True}}
        # Act
        providers = with_credential_apps(skeleton, credentials)
        # Assert
        assert providers["google"]["SCOPE"] == ["profile"]
        assert providers["google"]["OAUTH_PKCE_ENABLED"] is True

    def test_a_provider_without_credential_settings_keeps_its_configuration(self):
        # Arrange: no credentials declared for this provider at all
        # Act
        providers = with_credential_apps({"orcid": {"MEMBER_API": False}}, {"google": ("id", CANARY_SECRET)})
        # Assert
        assert providers["orcid"] == {"MEMBER_API": False}

    def test_the_input_configuration_is_not_mutated(self):
        # A settings-time helper that edited the dict it was handed would corrupt
        # every later reader of the deployment's provider configuration.
        # Arrange
        original = {"google": {"SCOPE": ["profile"]}}
        # Act
        with_credential_apps(original, {"google": ("id", CANARY_SECRET)})
        # Assert
        assert original == {"google": {"SCOPE": ["profile"]}}


# ---------------------------------------------------------------------------
# The wiring, asserted through allauth's own app resolution.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("provider", ["google", "orcid"])
def test_allauth_serves_a_provider_exactly_when_its_pair_is_complete(provider):
    """allauth's own view of the credentials agrees with the completeness rule."""
    # Arrange: the credential settings the running deployment composed
    from allauth.socialaccount.adapter import get_adapter
    from django.conf import settings as django_settings

    id_setting, secret_setting = {
        "google": ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"),
        "orcid": ("ORCID_CLIENT_ID", "ORCID_CLIENT_SECRET"),
    }[provider]

    # Act: allauth's own resolution, not this module's opinion of it
    apps = get_adapter().list_apps(None, provider=provider)

    # Assert
    assert bool(apps) == credential_is_complete(
        getattr(django_settings, id_setting, ""), getattr(django_settings, secret_setting, "")
    )


# ---------------------------------------------------------------------------
# What the visitor sees.
# ---------------------------------------------------------------------------


@pytest.mark.auth
class TestCompleteCredentialsPutTheButtonOnThePages:
    @pytest.mark.django_db
    def test_google_is_offered_on_both_pages(self, client, credential_settings):
        # Arrange
        credential_settings({"google": ("1234.apps.googleusercontent.com", CANARY_SECRET)})
        # Act
        signin_links = _social_links(client.get(SIGNIN_URL).content.decode("utf-8"))
        signup_links = _social_links(client.get(SIGNUP_URL).content.decode("utf-8"))
        # Assert
        assert GOOGLE_LOGIN_PATH in signin_links
        assert GOOGLE_LOGIN_PATH in signup_links

    @pytest.mark.django_db
    def test_orcid_is_offered_on_both_pages(self, client, credential_settings):
        # Arrange
        credential_settings({"orcid": ("APP-ORCID-ID", CANARY_SECRET)})
        # Act
        signin_links = _social_links(client.get(SIGNIN_URL).content.decode("utf-8"))
        signup_links = _social_links(client.get(SIGNUP_URL).content.decode("utf-8"))
        # Assert
        assert ORCID_LOGIN_PATH in signin_links
        assert ORCID_LOGIN_PATH in signup_links

    @pytest.mark.django_db
    def test_both_providers_are_offered_when_both_are_configured(self, client, credential_settings):
        # Arrange
        credential_settings(
            {
                "google": ("1234.apps.googleusercontent.com", CANARY_SECRET),
                "orcid": ("APP-ORCID-ID", CANARY_SECRET),
            }
        )
        # Act
        links = _social_links(client.get(SIGNIN_URL).content.decode("utf-8"))
        # Assert
        assert GOOGLE_LOGIN_PATH in links
        assert ORCID_LOGIN_PATH in links

    @pytest.mark.django_db
    def test_the_google_button_is_still_labelled(self, client, credential_settings):
        # Arrange
        credential_settings({"google": ("1234.apps.googleusercontent.com", CANARY_SECRET)})
        # Act
        body = client.get(SIGNIN_URL).content.decode("utf-8")
        # Assert
        assert "btn-google" in body


@pytest.mark.auth
class TestTheOfferedButtonStillWorks:
    """The whole point of deriving the button: what is offered can be clicked."""

    @pytest.mark.django_db
    def test_following_the_offered_google_link_does_not_500(self, client, credential_settings):
        # Arrange
        credential_settings({"google": ("1234.apps.googleusercontent.com", CANARY_SECRET)})
        offered = _social_links(client.get(SIGNIN_URL).content.decode("utf-8"))
        # Act
        response = client.get(offered[0])
        # Assert
        assert response.status_code != 500

    @pytest.mark.django_db
    def test_following_the_offered_google_link_goes_to_the_provider(self, client, credential_settings):
        # Arrange
        credential_settings({"google": ("1234.apps.googleusercontent.com", CANARY_SECRET)})
        offered = _social_links(client.get(SIGNIN_URL).content.decode("utf-8"))
        # Act
        response = client.get(offered[0])
        # Assert
        assert response.status_code in (301, 302)

    @pytest.mark.django_db
    def test_following_the_offered_orcid_link_does_not_500(self, client, credential_settings):
        # Arrange
        credential_settings({"orcid": ("APP-ORCID-ID", CANARY_SECRET)})
        offered = _social_links(client.get(SIGNIN_URL).content.decode("utf-8"))
        # Act
        response = client.get(offered[0])
        # Assert
        assert response.status_code != 500


@pytest.mark.auth
class TestIncompleteCredentialsOfferNothing:
    """No complete pair, no button — a half-configured app is never shipped."""

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "credentials",
        [
            {"google": ("1234.apps.googleusercontent.com", "")},
            {"google": ("", CANARY_SECRET)},
            {"google": ("CHANGEME", CANARY_SECRET)},
            {"google": ("your-client-id", "your-client-secret")},
            {},
        ],
    )
    def test_no_google_link_is_offered(self, client, credential_settings, credentials):
        # Arrange
        credential_settings(credentials)
        # Act
        links = _social_links(client.get(SIGNIN_URL).content.decode("utf-8"))
        # Assert
        assert GOOGLE_LOGIN_PATH not in links

    @pytest.mark.django_db
    def test_an_incomplete_orcid_stays_hidden_beside_a_configured_google(self, client, credential_settings):
        # Per provider, not all-or-nothing.
        # Arrange: Google complete, ORCID not
        credential_settings({"google": ("1234.apps.googleusercontent.com", CANARY_SECRET), "orcid": ("APP-ID", "")})
        # Act
        links = _social_links(client.get(SIGNIN_URL).content.decode("utf-8"))
        # Assert
        assert GOOGLE_LOGIN_PATH in links
        assert ORCID_LOGIN_PATH not in links


@pytest.mark.auth
class TestTheClientSecretNeverReachesThePage:
    @pytest.mark.django_db
    def test_the_google_secret_is_absent_from_the_signin_page(self, client, credential_settings):
        # Arrange
        credential_settings({"google": ("1234.apps.googleusercontent.com", CANARY_SECRET)})
        # Act
        body = client.get(SIGNIN_URL).content.decode("utf-8")
        # Assert
        assert CANARY_SECRET not in body

    @pytest.mark.django_db
    def test_the_google_secret_is_absent_from_the_signup_page(self, client, credential_settings):
        # Arrange
        credential_settings({"google": ("1234.apps.googleusercontent.com", CANARY_SECRET)})
        # Act
        body = client.get(SIGNUP_URL).content.decode("utf-8")
        # Assert
        assert CANARY_SECRET not in body

    @pytest.mark.django_db
    def test_the_orcid_secret_is_absent_from_the_signin_page(self, client, credential_settings):
        # Arrange
        credential_settings({"orcid": ("APP-ORCID-ID", CANARY_SECRET)})
        # Act
        body = client.get(SIGNIN_URL).content.decode("utf-8")
        # Assert
        assert CANARY_SECRET not in body


# ---------------------------------------------------------------------------
# A leftover database row is not a second app.
# ---------------------------------------------------------------------------


@pytest.mark.auth
class TestALeftoverDatabaseRowDoesNotBreakTheButton:
    """``manage.py setup_social_auth`` writes DB rows; the settings now also declare an app.

    allauth blends both sources and ``get_app`` REFUSES when more than one app
    is visible for a provider (``MultipleObjectsReturned``), which the login
    view turns into an HTTP 500. The settings are the declared source of truth,
    so they win for a provider they configure — the database row stays as an
    artefact, not as a rival.
    """

    @pytest.fixture
    def legacy_db_row(self, db):
        """The row an operator's earlier ``setup_social_auth`` run left behind."""
        app = SocialApp.objects.create(
            provider="google",
            name="Google",
            client_id="legacy-db-client-id",
            secret="legacy-db-secret",
        )
        app.sites.add(Site.objects.get_current())
        return app

    @pytest.mark.django_db
    def test_exactly_one_google_link_is_offered(self, client, credential_settings, legacy_db_row):
        # Arrange
        credential_settings({"google": ("1234.apps.googleusercontent.com", CANARY_SECRET)})
        # Act
        links = _social_links(client.get(SIGNIN_URL).content.decode("utf-8"))
        # Assert
        assert links.count(GOOGLE_LOGIN_PATH) == 1

    @pytest.mark.django_db
    def test_the_offered_link_still_does_not_500(self, client, credential_settings, legacy_db_row):
        # Arrange
        credential_settings({"google": ("1234.apps.googleusercontent.com", CANARY_SECRET)})
        offered = _social_links(client.get(SIGNIN_URL).content.decode("utf-8"))
        # Act
        response = client.get(offered[0])
        # Assert
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_the_database_row_alone_still_offers_a_button(self, client, credential_settings, legacy_db_row):
        # The pre-existing path must not be broken by the new one: a deployment
        # that configures providers ONLY through the database keeps working.
        # Arrange: no credentials in settings at all
        credential_settings({})
        # Act
        links = _social_links(client.get(SIGNIN_URL).content.decode("utf-8"))
        # Assert
        assert GOOGLE_LOGIN_PATH in links

    @pytest.mark.django_db
    def test_the_database_row_alone_still_does_not_500(self, client, credential_settings, legacy_db_row):
        # Arrange: no credentials in settings at all
        credential_settings({})
        offered = _social_links(client.get(SIGNIN_URL).content.decode("utf-8"))
        # Act
        response = client.get(offered[0])
        # Assert
        assert response.status_code == 302


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
