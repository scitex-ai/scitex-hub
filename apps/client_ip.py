"""Client IP derivation shared by every rate limiter and audit log.

Deployment chain: Cloudflare edge -> cloudflared -> (nginx) -> Django. The
edge sets ``CF-Connecting-IP`` and overwrites any value a client sends; nginx
sets ``X-Real-IP`` from its own peer address. ``X-Forwarded-For`` is NOT used:
its leftmost entry is whatever the client wrote, and every hop appends.

A forwarded header is honoured only when the direct peer (``REMOTE_ADDR``) is
one of ``settings.CLIENT_IP_TRUSTED_PROXIES``. A request that reaches Django
from anywhere else is keyed on ``REMOTE_ADDR`` alone, so a client cannot pick
its own rate-limit bucket by sending a header.
"""

from __future__ import annotations

import ipaddress
from functools import lru_cache

from django.conf import settings
from django.http import HttpRequest

#: Forwarded headers in precedence order (Django ``META`` names). Each is set
#: by infrastructure we run, never appended to from client input.
FORWARDED_IP_HEADERS = ("HTTP_CF_CONNECTING_IP", "HTTP_X_REAL_IP")

#: Loopback, RFC 1918 and ULA ranges: the Docker bridge networks nginx and
#: cloudflared reach Django from. Django is not published on a public address.
DEFAULT_TRUSTED_PROXIES = (
    "127.0.0.0/8",
    "::1/128",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "fc00::/7",
)

UNKNOWN_IP = "unknown"


@lru_cache(maxsize=8)
def _networks(cidrs: tuple[str, ...]) -> tuple:
    return tuple(ipaddress.ip_network(cidr.strip(), strict=False) for cidr in cidrs)


def _parse_ip(value: str | None):
    if not value:
        return None
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def is_trusted_proxy(address: str | None) -> bool:
    """True when ``address`` is a proxy whose forwarded headers we honour."""
    ip = _parse_ip(address)
    if ip is None:
        return False
    cidrs = tuple(
        getattr(settings, "CLIENT_IP_TRUSTED_PROXIES", DEFAULT_TRUSTED_PROXIES)
    )
    return any(ip in network for network in _networks(cidrs))


def get_client_ip(request: HttpRequest) -> str:
    """Return the address of the client that sent ``request``.

    Never raises and never returns attacker-chosen text: the result is either
    a parsed IP address or ``"unknown"``.
    """
    remote = _parse_ip(request.META.get("REMOTE_ADDR"))
    if remote is not None and is_trusted_proxy(str(remote)):
        for header in FORWARDED_IP_HEADERS:
            forwarded = _parse_ip(request.META.get(header))
            if forwarded is not None:
                return str(forwarded)
    return str(remote) if remote is not None else UNKNOWN_IP
