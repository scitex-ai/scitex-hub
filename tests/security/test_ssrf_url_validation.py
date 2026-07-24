"""Regression: tenant-supplied download URLs must be SSRF-validated by host.

api_file_upload_url (repository/api/file_ops_transfer.py) lets a tenant give the
server a URL to download. Checking only the scheme is not enough — the
destination HOST is what matters. is_safe_public_url resolves the host and
rejects any private/loopback/link-local/reserved address, blocking the loopback
Gitea (127.0.0.1), the cloud metadata endpoint (169.254.169.254), and RFC1918
management/DB hosts. Delete that and it's SSRF again.

DB-free + mock-free + NETWORK-free: every case uses an IP literal or ``localhost``
so getaddrinfo resolves locally without touching the network.
"""
from __future__ import annotations

import pytest

from apps.infra.project_app.url_safety import is_safe_public_url

pytestmark = pytest.mark.security


def test_rejects_loopback_ip():
    # Arrange
    url = "http://127.0.0.1:3000/api/v1/user"
    # Act
    safe, _reason = is_safe_public_url(url)
    # Assert
    assert safe is False


def test_rejects_cloud_metadata_ip():
    # Arrange
    url = "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
    # Act
    safe, _reason = is_safe_public_url(url)
    # Assert
    assert safe is False


def test_rejects_rfc1918_private_ip():
    # Arrange
    url = "http://10.0.0.5/"
    # Act
    safe, _reason = is_safe_public_url(url)
    # Assert
    assert safe is False


def test_rejects_ipv6_loopback():
    # Arrange
    url = "http://[::1]:5432/"
    # Act
    safe, _reason = is_safe_public_url(url)
    # Assert
    assert safe is False


def test_rejects_non_http_scheme():
    # Arrange
    url = "file:///etc/passwd"
    # Act
    safe, _reason = is_safe_public_url(url)
    # Assert
    assert safe is False


def test_rejects_localhost_hostname():
    # Arrange
    url = "http://localhost/"
    # Act
    safe, _reason = is_safe_public_url(url)
    # Assert
    assert safe is False


def test_allows_a_public_ip():
    # Arrange
    url = "http://93.184.216.34/"  # a public address literal (no DNS needed)
    # Act
    safe, _reason = is_safe_public_url(url)
    # Assert
    assert safe is True
