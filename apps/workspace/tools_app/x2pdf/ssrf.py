"""Fetch a user-supplied URL without letting it reach the hub's own network.

Every hop (the first request and each redirect) is resolved, every resolved
address must be globally routable, and the connection is pinned to the checked
address so a second DNS answer cannot swap in a private one.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable
from urllib.parse import urljoin, urlsplit

ALLOWED_SCHEMES = ("http", "https")
REDIRECT_CODES = (301, 302, 303, 307, 308)
USER_AGENT = "Mozilla/5.0 (compatible; SciTeX-X2PDF/1.0; +https://scitex.ai)"


class UnsafeURLError(ValueError):
    """The URL is malformed, uses a forbidden scheme, or points inward."""


class FetchError(RuntimeError):
    """The remote fetch failed for a reason worth showing the user."""


@dataclass(frozen=True)
class Target:
    url: str
    scheme: str
    host: str
    port: int
    path: str
    ips: tuple[str, ...]


@dataclass
class FetchResult:
    url: str
    status: int
    headers: dict = field(default_factory=dict)
    body: bytes = b""

    @property
    def content_type(self) -> str:
        return (self.headers.get("content-type") or "").split(";")[0].strip().lower()


def is_public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value.split("%")[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        embedded = ip.ipv4_mapped or ip.sixtofour or (ip.teredo[1] if ip.teredo else None)
        if embedded is not None and not is_public_ip(str(embedded)):
            return False
    return bool(ip.is_global) and not (
        ip.is_multicast or ip.is_unspecified or ip.is_reserved or ip.is_loopback
    )


def _default_resolver(host: str, port: int) -> list[str]:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [info[4][0] for info in infos]


def validate_url(url: str, resolver: Callable[[str, int], Iterable[str]] | None = None) -> Target:
    if not isinstance(url, str) or len(url) > 4096 or any(c in url for c in "\r\n\x00"):
        raise UnsafeURLError("Invalid URL.")
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UnsafeURLError("Only http and https URLs can be converted.")
    try:
        host = parts.hostname
        port = parts.port or (443 if scheme == "https" else 80)
    except ValueError as exc:
        raise UnsafeURLError("Invalid URL.") from exc
    if not host:
        raise UnsafeURLError("The URL has no host.")
    try:
        ips = tuple(dict.fromkeys((resolver or _default_resolver)(host, port)))
    except (OSError, UnicodeError) as exc:
        raise UnsafeURLError(f"Could not resolve {host}.") from exc
    if not ips:
        raise UnsafeURLError(f"Could not resolve {host}.")
    if not all(is_public_ip(ip) for ip in ips):
        raise UnsafeURLError("That address is on a private or local network and cannot be fetched.")
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    return Target(url=url.strip(), scheme=scheme, host=host, port=port, path=path, ips=ips)


def _open_pinned(target: Target, ip: str, headers: dict, timeout: float):
    """Open one request against ``ip`` while presenting ``target.host`` for TLS/Host."""
    import certifi
    import urllib3

    kw = dict(timeout=urllib3.Timeout(connect=min(10.0, timeout), read=timeout), retries=False, maxsize=1)
    if target.scheme == "https":
        pool = urllib3.HTTPSConnectionPool(
            ip, target.port, cert_reqs="CERT_REQUIRED", ca_certs=certifi.where(),
            server_hostname=target.host, assert_hostname=target.host, **kw,
        )
    else:
        pool = urllib3.HTTPConnectionPool(ip, target.port, **kw)
    resp = pool.urlopen("GET", target.path, headers=headers, redirect=False,
                        preload_content=False, retries=False)
    return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.stream(64 * 1024), resp


def safe_fetch(
    url: str,
    *,
    max_bytes: int = 25 * 1024 * 1024,
    timeout: float = 20.0,
    max_redirects: int = 5,
    accept: str = "*/*",
    resolver: Callable[[str, int], Iterable[str]] | None = None,
    opener: Callable | None = None,
) -> FetchResult:
    opener = opener or _open_pinned
    deadline = time.monotonic() + timeout * 2
    current = url
    for _hop in range(max_redirects + 1):
        target = validate_url(current, resolver)
        default_port = 443 if target.scheme == "https" else 80
        hostpart = f"[{target.host}]" if ":" in target.host else target.host
        host_header = hostpart if target.port == default_port else f"{hostpart}:{target.port}"
        headers = {"Host": host_header, "User-Agent": USER_AGENT, "Accept": accept,
                   "Accept-Encoding": "identity"}
        try:
            status, resp_headers, chunks, raw = opener(target, target.ips[0], headers, timeout)
        except UnsafeURLError:
            raise
        except Exception as exc:
            raise FetchError(f"Could not fetch {target.host}: {exc.__class__.__name__}.") from exc
        try:
            if status in REDIRECT_CODES and resp_headers.get("location"):
                current = urljoin(target.url, resp_headers["location"])
                continue
            body = bytearray()
            for chunk in chunks:
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise FetchError(f"The page is larger than {max_bytes // (1024 * 1024)} MB.")
                if time.monotonic() > deadline:
                    raise FetchError("The page took too long to download.")
            return FetchResult(url=target.url, status=status, headers=resp_headers, body=bytes(body))
        finally:
            release = getattr(raw, "release_conn", None)
            if release:
                release()
    raise FetchError("Too many redirects.")
