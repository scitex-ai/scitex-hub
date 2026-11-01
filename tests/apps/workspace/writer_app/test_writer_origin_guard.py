"""Writer compile origin checks use Django's actual CSRF origin policy."""

import pytest
from django.core.exceptions import DisallowedHost
from django.test import RequestFactory, override_settings

from apps.workspace.writer_app._origin_policy import is_cross_origin_write as _is_cross_origin_write


@pytest.mark.parametrize(
    "origin,refused",
    [
        ("https://compute-03-net.scitex.ai", False),
        ("https://other.scitex.ai", False),
        ("https://evil.example", True),
        ("https://scitex.ai.evil.example", True),
        ("http://other.scitex.ai", True),
        ("http://compute-03-net.scitex.ai", False),
        ("null", True),
        ("https://[invalid", True),
    ],
)
def test_configured_wildcard_tunnel_origin_is_scheme_bound(origin, refused):
    # Arrange
    request = RequestFactory().post(
        "/apps/writer/api/compile", HTTP_HOST="compute-03-net.scitex.ai",
        HTTP_ORIGIN=origin,
    )
    # Act
    with override_settings(
        ALLOWED_HOSTS=["compute-03-net.scitex.ai"],
        CSRF_TRUSTED_ORIGINS=["https://*.scitex.ai"],
        SECURE_PROXY_SSL_HEADER=None,
    ):
        result = _is_cross_origin_write(request)
    # Assert
    assert result is refused


@pytest.mark.parametrize(
    "trusted_proxy,refused",
    [(None, True), (("HTTP_X_FORWARDED_PROTO", "https"), False)],
)
def test_forwarded_scheme_is_used_only_when_explicitly_trusted(trusted_proxy, refused):
    # Arrange
    request = RequestFactory().post(
        "/apps/writer/api/compile", HTTP_HOST="compute-03-net.scitex.ai",
        HTTP_ORIGIN="https://compute-03-net.scitex.ai",
        HTTP_X_FORWARDED_PROTO="https",
    )
    # Act
    with override_settings(
        ALLOWED_HOSTS=["compute-03-net.scitex.ai"],
        CSRF_TRUSTED_ORIGINS=[], SECURE_PROXY_SSL_HEADER=trusted_proxy,
    ):
        result = _is_cross_origin_write(request)
    # Assert
    assert result is refused


def test_allowed_host_membership_does_not_trust_another_origin():
    # Arrange
    request = RequestFactory().post(
        "/apps/writer/api/compile", HTTP_HOST="compute-03-net.scitex.ai",
        HTTP_ORIGIN="https://other.scitex.ai", secure=True,
    )
    # Act
    with override_settings(
        ALLOWED_HOSTS=[".scitex.ai"], CSRF_TRUSTED_ORIGINS=[],
        SECURE_PROXY_SSL_HEADER=None,
    ):
        result = _is_cross_origin_write(request)
    # Assert
    assert result is True


def test_invalid_host_is_still_refused_even_with_a_trusted_origin():
    # Arrange
    request = RequestFactory().post(
        "/apps/writer/api/compile", HTTP_HOST="evil.example",
        HTTP_ORIGIN="https://compute-03-net.scitex.ai",
    )
    # Act
    with override_settings(
        ALLOWED_HOSTS=["compute-03-net.scitex.ai"],
        CSRF_TRUSTED_ORIGINS=["https://*.scitex.ai"],
    ):
        # Assert
        with pytest.raises(DisallowedHost):
            _is_cross_origin_write(request)
