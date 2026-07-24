"""SSRF-resistant validation + fetch for tenant-supplied URLs.

A tenant can hand the server an arbitrary URL to download (e.g.
api_file_upload_url). A bare ``requests.get(url)`` lets that tenant reach
internal services the tenant must never touch — the loopback Gitea
(127.0.0.1:3000), the cloud metadata endpoint (169.254.169.254), and RFC1918
management / database hosts — i.e. Server-Side Request Forgery. Checking only
the URL *scheme* is not enough; the destination *host* is what matters, and a
public host can redirect to an internal one.

This module resolves the host to its actual IP(s) and rejects any non-public
address, re-validating on every redirect hop.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

_ALLOWED_SCHEMES = ("http", "https")
_MAX_REDIRECTS = 5


def is_safe_public_url(url: str) -> tuple[bool, str]:
    """Return ``(True, "")`` if ``url`` targets a PUBLIC host, else ``(False, reason)``.

    Rejects non-http(s) schemes and any host that resolves to a private,
    loopback, link-local, reserved, multicast, or unspecified address — which
    covers 127.0.0.0/8, 169.254.0.0/16 (cloud metadata), RFC1918, ::1 and
    fc00::/7. Resolution is done here (not left to requests) so the decision is
    made on the real destination IP, defeating hostname tricks.
    """
    try:
        parsed = urlparse(url)
    except Exception as exc:  # pragma: no cover - urlparse rarely raises
        return False, f"unparseable URL: {exc}"
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return False, f"scheme {parsed.scheme!r} not allowed (http/https only)"
    host = parsed.hostname
    if not host:
        return False, "URL has no host"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        return False, f"host {host!r} does not resolve: {exc}"
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, f"unparseable resolved address {ip_str!r}"
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False, f"host {host!r} resolves to non-public address {ip_str}"
    return True, ""


def fetch_public_url(url, *, timeout=30, headers=None, max_redirects=_MAX_REDIRECTS):
    """GET ``url``, following redirects but re-validating each hop is public.

    Raises ValueError if any hop targets a non-public host (SSRF) or there are
    too many redirects. Returns a streaming ``requests.Response`` for the final
    hop. ``requests`` is imported lazily so is_safe_public_url stays testable
    with only the standard library.
    """
    import requests  # lazy: keeps the validator stdlib-only

    current = url
    for _ in range(max_redirects + 1):
        ok, reason = is_safe_public_url(current)
        if not ok:
            raise ValueError(f"blocked URL (SSRF protection): {reason}")
        resp = requests.get(
            current,
            timeout=timeout,
            stream=True,
            allow_redirects=False,
            headers=headers,
        )
        if resp.is_redirect or resp.is_permanent_redirect:
            location = resp.headers.get("Location")
            resp.close()
            if not location:
                raise ValueError("redirect without a Location header")
            current = urljoin(current, location)
            continue
        return resp
    raise ValueError("too many redirects")
