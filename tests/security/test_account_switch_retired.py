"""The password-less multi-account switcher is gone, and so is its cookie.

Switching used a long-lived ``device_id`` cookie as the only credential for
every account ever used in that browser. The switcher had no UI left, so it is
removed rather than repaired. These tests drive the real URLconf through the
Django test client: the routes must not resolve, and sign-in / sign-out must
expire any ``device_id`` cookie an old browser still holds.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client

pytestmark = [pytest.mark.security, pytest.mark.django_db]

PASSWORD = "Correct-Horse-Battery-9"  # pragma: allowlist secret


@pytest.fixture
def account():
    return User.objects.create_user(
        username="switch-probe", email="switch-probe@example.org", password=PASSWORD
    )


@pytest.fixture
def stale_cookie_client():
    client = Client()
    client.cookies["device_id"] = "00000000-0000-4000-8000-000000000000"
    return client


def test_switch_route_no_longer_resolves(account, stale_cookie_client):
    # Arrange
    url = f"/auth/switch/{account.pk}/"
    # Act
    response = stale_cookie_client.get(url)
    # Assert
    assert response.status_code == 404


def test_switch_route_does_not_sign_anyone_in(account, stale_cookie_client):
    # Arrange
    url = f"/auth/switch/{account.pk}/?next=https://example.com/"
    # Act
    stale_cookie_client.get(url)
    # Assert
    assert "_auth_user_id" not in stale_cookie_client.session


def test_authenticated_accounts_listing_no_longer_resolves(account):
    # Arrange
    client = Client()
    client.force_login(account)
    # Act
    response = client.get("/auth/api/authenticated-accounts/")
    # Assert
    assert response.status_code == 404


def test_sign_in_expires_legacy_device_cookie(account, stale_cookie_client):
    # Arrange
    form = {"username": account.username, "password": PASSWORD}
    # Act
    response = stale_cookie_client.post("/auth/signin/", form)
    # Assert
    assert response.cookies["device_id"]["max-age"] == 0


def test_sign_out_expires_legacy_device_cookie(account, stale_cookie_client):
    # Arrange
    stale_cookie_client.force_login(account)
    # Act
    response = stale_cookie_client.get("/auth/logout/")
    # Assert
    assert response.cookies["device_id"]["max-age"] == 0
