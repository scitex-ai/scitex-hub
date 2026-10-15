#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The ORCID base domain is an EXACT allowlist, because the client secret follows it.

FOUND BY REVIEW, and it is a secret-exfiltration path: ``ORCID_BASE_DOMAIN`` was
read straight from the environment into ``SOCIALACCOUNT_PROVIDERS["orcid"]
["BASE_DOMAIN"]``, and allauth's ``OrcidOAuth2Adapter`` builds its endpoints by
string concatenation at import time::

    authorize_url    = f"https://{base_domain}/oauth/authorize"
    access_token_url = f"https://{api_domain}/oauth/token"      # api_domain = f"pub.{base_domain}"

So ``ORCID_BASE_DOMAIN=attacker.invalid`` produced ``https://pub.attacker.invalid/
oauth/token`` — a host the deployment does not own, to which the OAuth2 client
POSTS the client id AND CLIENT SECRET at the token exchange. There is no error,
no warning, and no visible difference on the page: the button works, and the
secret walks out of the building.

WHY AN ALLOWLIST AND NOT A SANITISER. "Looks like a hostname" is the wrong test —
``attacker.invalid`` IS a hostname. ORCID has exactly two deployment hosts, so
the value must be one of them, compared after the smallest possible normalisation
(scheme, trailing slash, case) so that ``https://orcid.org/`` is accepted rather
than surprising an operator. Anything else raises at settings load, because a
settings import that cannot build a safe endpoint should not boot with a
half-built one.

THE HOST ASSERTIONS ARE THE POINT. Rejecting bad input is only half of it: these
tests also pin WHERE the accepted values point — the authorize host and the token
host, for both the ``pub`` and ``api`` variants — and they assert against the
LIVE adapter, so a change that bypasses the validator (a different key, a new
setting, a hand-edited provider config) fails here rather than on the wire.
"""

import os
from urllib.parse import urlparse

import pytest

from config.social_apps import ORCID_ALLOWED_BASE_DOMAINS, orcid_base_domain

#: Values an attacker (or a hurried operator) might supply. None of them is ORCID.
REJECTED_VALUES = (
    "attacker.invalid",
    "pub.attacker.invalid",
    "orcid.org.attacker.invalid",
    "attacker-orcid.org",
    "orcid.org.evil.example",
    "orcid.org:8443",
    "https://attacker.invalid",
    "https://attacker.invalid/?next=orcid.org",
    "sandbox.orcid.org.attacker.invalid",
    "localhost",
    "127.0.0.1",
)

#: The same two hosts written the several ways an operator legitimately might.
ACCEPTED_VALUES = (
    ("orcid.org", "orcid.org"),
    ("sandbox.orcid.org", "sandbox.orcid.org"),
    ("ORCID.ORG", "orcid.org"),
    ("Sandbox.Orcid.Org", "sandbox.orcid.org"),
    ("https://orcid.org", "orcid.org"),
    ("https://sandbox.orcid.org/", "sandbox.orcid.org"),
    ("  https://orcid.org  ", "orcid.org"),
)


def _endpoint_hosts(base_domain, *, member_api=False):
    """The hosts allauth's ORCID adapter builds from ``base_domain``.

    Reproduced from allauth/socialaccount/providers/orcid/views.py, so a test can
    ask "which host would the secret go to?" without an HTTP client.
    """
    api_domain = f"{'api' if member_api else 'pub'}.{base_domain}"
    return {
        "authorize": urlparse(f"https://{base_domain}/oauth/authorize").netloc,
        "access_token": urlparse(f"https://{api_domain}/oauth/token").netloc,
    }


@pytest.mark.guards(
    defect=(
        "ORCID_BASE_DOMAIN was passed unvalidated from the environment into "
        "allauth's ORCID adapter, whose token endpoint is "
        "f'https://pub.{BASE_DOMAIN}/oauth/token' — so the value "
        "attacker.invalid made the client SECRET be POSTed to a host the "
        "deployment does not own."
    )
)
class TestTheAllowlistIsExact:
    def test_the_allowlist_holds_only_orcids_two_hosts(self):
        # Arrange / Act
        allowed = ORCID_ALLOWED_BASE_DOMAINS
        # Assert
        assert sorted(allowed) == ["orcid.org", "sandbox.orcid.org"]

    @pytest.mark.parametrize("supplied,expected", ACCEPTED_VALUES)
    def test_a_legitimate_host_is_accepted_in_the_forms_operators_write_it(self, supplied, expected):
        # Arrange / Act
        resolved = orcid_base_domain(supplied)
        # Assert
        assert resolved == expected

    @pytest.mark.parametrize("value", REJECTED_VALUES)
    def test_a_host_outside_the_allowlist_is_refused(self, value):
        # Arrange: a value that would send the client secret to the wrong host
        # Act / Assert
        with pytest.raises(ValueError):
            orcid_base_domain(value)

    def test_an_absent_value_falls_back_to_the_sandbox(self):
        # Arrange: unset, or set-but-empty, which is what the dev env file ships
        # Act
        for supplied in (None, "", "   "):
            resolved = orcid_base_domain(supplied)
            # Assert
            assert resolved == "sandbox.orcid.org"

    def test_the_default_is_itself_allowlisted(self):
        # A default that is not on the list would be the same defect with a
        # friendlier face.
        # Arrange / Act
        default = orcid_base_domain(None)
        # Assert
        assert default in ORCID_ALLOWED_BASE_DOMAINS


@pytest.mark.guards(
    defect=(
        "The ORCID authorize and token hosts were built by string "
        "concatenation from a free-form base domain, so nothing pinned "
        "WHICH host the accepted configurations point at."
    )
)
class TestWhereTheAcceptedValuesPoint:
    """Assert the endpoint HOSTS, not just that the input was accepted."""

    @pytest.mark.parametrize("value", sorted(ORCID_ALLOWED_BASE_DOMAINS))
    def test_the_authorize_and_token_hosts_stay_inside_the_allowlist(self, value):
        # Arrange / Act
        hosts = _endpoint_hosts(value)
        # Assert
        assert hosts["authorize"] == value
        assert hosts["access_token"] == f"pub.{value}"

    @pytest.mark.parametrize("value", sorted(ORCID_ALLOWED_BASE_DOMAINS))
    def test_the_member_api_token_host_stays_inside_the_allowlist(self, value):
        # The api.* variant is a second host built from the same value, so it
        # needs the same assertion.
        # Arrange / Act
        hosts = _endpoint_hosts(value, member_api=True)
        # Assert
        assert hosts["access_token"] == f"api.{value}"

    @pytest.mark.parametrize("value", REJECTED_VALUES)
    def test_no_endpoint_can_be_built_from_a_refused_value(self, value):
        # The refusal happens before any URL exists: the validator raises, so
        # there is no endpoint — and therefore no secret — to hand to a host.
        # Arrange / Act / Assert
        with pytest.raises(ValueError):
            orcid_base_domain(value)

    def test_pass_through_is_what_would_hand_over_the_secret(self):
        # THE PREMISE OF THIS FILE, asserted so the guard cannot be vacuous: this
        # is the endpoint that `ORCID_BASE_DOMAIN=attacker.invalid` built before
        # the allowlist existed, and it is the URL the client id and secret are
        # POSTed to at the token exchange.
        # Arrange / Act
        hosts = _endpoint_hosts("attacker.invalid")
        # Assert
        assert hosts["access_token"] == "pub.attacker.invalid"


@pytest.mark.guards(
    defect=(
        "The deployment could hold an ORCID base domain outside "
        "orcid.org/sandbox.orcid.org and still boot: neither the settings "
        "nor the live adapter endpoints were asserted against the allowlist."
    )
)
class TestTheLiveDeploymentUsesTheAllowlistedHosts:
    """The running configuration, asserted rather than assumed."""

    def test_the_live_adapter_authorizes_on_an_allowlisted_host(self):
        # Arrange
        from allauth.socialaccount.providers.orcid.views import OrcidOAuth2Adapter

        # Act
        host = urlparse(OrcidOAuth2Adapter.authorize_url).netloc
        # Assert
        assert host in ORCID_ALLOWED_BASE_DOMAINS

    def test_the_live_adapter_exchanges_the_token_on_an_allowlisted_host(self):
        # THIS is the host that receives the client secret.
        # Arrange
        from allauth.socialaccount.providers.orcid.views import OrcidOAuth2Adapter

        # Act
        host = urlparse(OrcidOAuth2Adapter.access_token_url).netloc
        # Assert
        assert host.split(".", 1)[-1] in ORCID_ALLOWED_BASE_DOMAINS
        assert host.split(".")[0] in ("pub", "api")

    def test_the_settings_value_is_the_validated_one(self):
        # The wiring, not just the helper: whatever the environment says, the
        # provider configuration holds a value this module accepted.
        # Arrange
        from django.conf import settings as django_settings

        # Act
        configured = django_settings.SOCIALACCOUNT_PROVIDERS["orcid"]["BASE_DOMAIN"]
        expected = orcid_base_domain(os.environ.get("ORCID_BASE_DOMAIN"))
        # Assert
        assert configured == expected
        assert configured in ORCID_ALLOWED_BASE_DOMAINS


if __name__ == "__main__":
    import os as _os

    pytest.main([_os.path.abspath(__file__)])

# EOF
