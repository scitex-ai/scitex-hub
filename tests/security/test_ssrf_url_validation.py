"""Regression: tenant-supplied download URLs must be SSRF-safe by *connection*.

api_file_upload_url (repository/api/file_ops_transfer.py) lets a tenant give the
server a URL to download. Two things must hold:

1. HOST validation, not just scheme — the destination host is resolved and any
   private/loopback/link-local/reserved address is rejected, blocking the
   loopback Gitea (127.0.0.1), the cloud metadata endpoint (169.254.169.254),
   and RFC1918 management/DB hosts.

2. The connection must go to the address that was VALIDATED. Validating the host
   and then letting ``requests`` connect by hostname re-resolves DNS a second
   time, so an attacker who controls DNS for their host (TTL 0) can answer
   PUBLIC for the check and INTERNAL for the fetch — a DNS-rebinding TOCTOU.
   ``fetch_public_url`` resolves once and PINS the vetted IP for the socket, so
   no second resolution can retarget it. Every redirect hop is pinned the same
   way.

Tests use real IP literals / a real loopback HTTP server, and hand-rolled
resolver / connector fakes passed as arguments (dependency injection at the
production API) — no network to the outside and no fixture mocking.
"""
from __future__ import annotations

import contextlib
import http.server
import socket
import threading

import pytest

from apps.infra.project_app.url_safety import (
    _pinned_ip_adapter,
    _resolve_public_addresses,
    fetch_public_url,
    is_safe_public_url,
)

pytestmark = pytest.mark.security


# --------------------------------------------------------------------------- #
# is_safe_public_url — host validation (no network: IP literals / localhost)   #
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# _resolve_public_addresses — single resolution, reject any non-public         #
# --------------------------------------------------------------------------- #
def test_resolve_rejects_private_literal_host():
    # Arrange
    host, port = "10.0.0.5", 80
    # Act
    # Assert
    with pytest.raises(ValueError):
        _resolve_public_addresses(host, port)


def test_resolve_returns_public_literal_host():
    # Arrange
    host, port = "93.184.216.34", 80
    # Act
    addresses = _resolve_public_addresses(host, port)
    # Assert
    assert addresses == [(socket.AF_INET, "93.184.216.34")]


# --------------------------------------------------------------------------- #
# Hand-rolled collaborators (passed as arguments — dependency injection)        #
# --------------------------------------------------------------------------- #
class _CountingResolver:
    """Stands in for the host resolver; records how many times it is called."""

    def __init__(self, addresses):
        self.addresses = addresses
        self.calls = 0

    def __call__(self, host, port):
        self.calls += 1
        return list(self.addresses)


class _RecordingConnector:
    """Stands in for urllib3's socket connector; records the target IP and
    aborts before any real network I/O."""

    def __init__(self):
        self.targets = []

    def __call__(self, address, timeout=None, source_address=None, socket_options=None):
        self.targets.append(address[0])
        raise ConnectionRefusedError(f"test-blocked connect to {address[0]}")


# --------------------------------------------------------------------------- #
# fetch_public_url — refuse / pin / single-resolution                          #
# --------------------------------------------------------------------------- #
def test_fetch_rejects_non_http_scheme():
    # Arrange
    url = "file:///etc/passwd"
    # Act
    # Assert
    with pytest.raises(ValueError):
        fetch_public_url(url)


def test_fetch_refuses_private_host():
    # Arrange
    url = "http://10.0.0.5/secret"
    # Act
    # Assert
    with pytest.raises(ValueError):
        fetch_public_url(url, timeout=2)


def test_fetch_makes_no_connection_when_host_is_private():
    # Arrange
    connector = _RecordingConnector()
    # Act
    with contextlib.suppress(ValueError):
        fetch_public_url("http://10.0.0.5/secret", timeout=2, _connector=connector)
    # Assert
    assert connector.targets == []


def test_fetch_connects_only_to_the_single_vetted_ip():
    # Arrange: the host would rebind to 169.254.169.254 on a second lookup, but
    # fetch resolves once (to the public IP) and pins it.
    resolver = _CountingResolver([(socket.AF_INET, "93.184.216.34")])
    connector = _RecordingConnector()
    # Act
    with contextlib.suppress(Exception):
        fetch_public_url(
            "http://rebind.evil/file.bin", timeout=2,
            _resolver=resolver, _connector=connector,
        )
    # Assert: the socket targeted only the vetted public IP, never an internal one.
    assert connector.targets == ["93.184.216.34"]


def test_fetch_resolves_host_exactly_once():
    # Arrange
    resolver = _CountingResolver([(socket.AF_INET, "93.184.216.34")])
    connector = _RecordingConnector()
    # Act
    with contextlib.suppress(Exception):
        fetch_public_url(
            "http://rebind.evil/file.bin", timeout=2,
            _resolver=resolver, _connector=connector,
        )
    # Assert
    assert resolver.calls == 1


# --------------------------------------------------------------------------- #
# real loopback server: the pin connects to the given IP, keeps the Host header #
# --------------------------------------------------------------------------- #
class _EchoHostHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = ("HOST=" + self.headers.get("Host", "")).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence access logging
        pass


@pytest.fixture
def loopback_server():
    srv = http.server.HTTPServer(("127.0.0.1", 0), _EchoHostHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield srv.server_address[1]
    finally:
        srv.shutdown()


def test_pinned_adapter_connects_to_ip_and_preserves_host_header(loopback_server):
    # Arrange: pin to loopback; the URL host is a name that never resolves, so a
    # response at all proves the socket used the pinned IP and the Host header
    # echoed back is the original hostname (vhost / SNI correctness).
    import requests

    session = requests.Session()
    session.mount("http://", _pinned_ip_adapter("127.0.0.1"))
    # Act
    resp = session.get(f"http://pinned-not-real.invalid:{loopback_server}/", timeout=5)
    # Assert
    assert resp.text == f"HOST=pinned-not-real.invalid:{loopback_server}"


def test_fetch_streams_body_from_pinned_ip(loopback_server):
    # Arrange: inject a resolver returning the loopback server's IP (loopback is
    # otherwise refused) so the real connect + stream path is exercised.
    def resolver(host, port):
        return [(socket.AF_INET, "127.0.0.1")]

    # Act
    resp = fetch_public_url(
        f"http://download.example:{loopback_server}/f.bin",
        timeout=5,
        _resolver=resolver,
    )
    body = b"".join(resp.iter_content(chunk_size=8192))
    # Assert
    assert body == f"HOST=download.example:{loopback_server}".encode()
