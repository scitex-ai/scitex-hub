"""Client IP derivation: forwarded headers count only from a trusted proxy.

Rate limits and login audit rows are keyed on ``apps.client_ip.get_client_ip``.
These tests drive real requests (RequestFactory for the helper, the Django test
client for a throttled endpoint) and assert that a client cannot choose its own
rate-limit bucket by sending ``X-Forwarded-For`` or ``CF-Connecting-IP``.
"""

from __future__ import annotations

import pytest
from django.core.cache import cache
from django.test import Client, RequestFactory, override_settings

from apps.client_ip import get_client_ip

pytestmark = pytest.mark.security

PUBLIC_PEER = "203.0.113.7"
PROXY_PEER = "172.18.0.5"


def _request(**meta):
    return RequestFactory().get("/", **meta)


def test_direct_client_forwarded_headers_are_ignored():
    # Arrange
    request = _request(
        REMOTE_ADDR=PUBLIC_PEER,
        HTTP_X_FORWARDED_FOR="10.0.0.1",
        HTTP_CF_CONNECTING_IP="10.0.0.2",
        HTTP_X_REAL_IP="10.0.0.3",
    )
    # Act
    ip = get_client_ip(request)
    # Assert
    assert ip == PUBLIC_PEER


def test_trusted_proxy_uses_cf_connecting_ip():
    # Arrange
    request = _request(
        REMOTE_ADDR=PROXY_PEER,
        HTTP_CF_CONNECTING_IP="198.51.100.20",
        HTTP_X_REAL_IP="198.51.100.21",
        HTTP_X_FORWARDED_FOR="1.2.3.4, 198.51.100.20",
    )
    # Act
    ip = get_client_ip(request)
    # Assert
    assert ip == "198.51.100.20"


def test_trusted_proxy_falls_back_to_x_real_ip():
    # Arrange
    request = _request(REMOTE_ADDR=PROXY_PEER, HTTP_X_REAL_IP="198.51.100.21")
    # Act
    ip = get_client_ip(request)
    # Assert
    assert ip == "198.51.100.21"


def test_x_forwarded_for_is_never_used_even_from_a_proxy():
    # Arrange
    request = _request(REMOTE_ADDR=PROXY_PEER, HTTP_X_FORWARDED_FOR="1.2.3.4")
    # Act
    ip = get_client_ip(request)
    # Assert
    assert ip == PROXY_PEER


def test_malformed_forwarded_value_is_skipped():
    # Arrange
    request = _request(
        REMOTE_ADDR=PROXY_PEER,
        HTTP_CF_CONNECTING_IP="not-an-ip; DROP",
        HTTP_X_REAL_IP="198.51.100.21",
    )
    # Act
    ip = get_client_ip(request)
    # Assert
    assert ip == "198.51.100.21"


def test_missing_remote_addr_is_unknown():
    # Arrange
    request = _request()
    request.META.pop("REMOTE_ADDR", None)
    # Act
    ip = get_client_ip(request)
    # Assert
    assert ip == "unknown"


@override_settings(CLIENT_IP_TRUSTED_PROXIES=("0.0.0.0/32",))
def test_no_trusted_proxy_configured_means_peer_address():
    # Arrange
    request = _request(REMOTE_ADDR=PROXY_PEER, HTTP_CF_CONNECTING_IP="198.51.100.20")
    # Act
    ip = get_client_ip(request)
    # Assert
    assert ip == PROXY_PEER


@pytest.mark.django_db
def test_rotating_x_forwarded_for_does_not_escape_the_ip_rate_limit():
    """Six token-mint attempts from one address hit the 5/min per-IP cap.

    Each attempt uses a different username (so the per-username counter never
    trips) and a different forged ``X-Forwarded-For``. With leftmost-XFF keying
    every attempt landed in a fresh bucket and none was refused.
    """
    # Arrange
    cache.clear()
    client = Client()
    # Act
    statuses = [
        client.post(
            "/api/me/token/",
            {"username": f"nobody-{i}", "password": "wrong"},
            content_type="application/json",
            REMOTE_ADDR=PUBLIC_PEER,
            HTTP_X_FORWARDED_FOR=f"198.51.100.{i}",
        ).status_code
        for i in range(6)
    ]
    cache.clear()
    # Assert
    assert statuses == [401, 401, 401, 401, 401, 429]
