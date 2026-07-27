"""SSRF-resistant validation + fetch for tenant-supplied URLs.

A tenant can hand the server an arbitrary URL to download (e.g.
api_file_upload_url). A bare ``requests.get(url)`` lets that tenant reach
internal services the tenant must never touch — the loopback Gitea
(127.0.0.1:3000), the cloud metadata endpoint (169.254.169.254), and RFC1918
management / database hosts — i.e. Server-Side Request Forgery. Checking only
the URL *scheme* is not enough; the destination *host* is what matters, and a
public host can redirect to an internal one.

Resolving the host, checking the IP, and THEN letting ``requests`` connect by
*hostname* is ALSO not enough: ``requests``/``urllib3`` perform a SECOND,
independent DNS resolution when they open the socket. An attacker who controls
DNS for their host (TTL 0) answers with a public address for our validation
lookup and an internal address (169.254.169.254 / 127.0.0.1 / RFC1918) for the
connection lookup — a DNS-rebinding TOCTOU that makes the check theatre.

This module closes that gap: it resolves the host EXACTLY ONCE, refuses unless
EVERY returned address is public, then PINS the connection to one of those
vetted addresses (via urllib3's ``_dns_host``) so no second resolution can
retarget the socket. The ``Host`` header, TLS SNI, and certificate hostname all
stay the original hostname, so ordinary HTTPS keeps working. Every redirect hop
is resolved, validated, and pinned the same way.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

_ALLOWED_SCHEMES = ("http", "https")
_MAX_REDIRECTS = 5
_DEFAULT_TIMEOUT = 30


def _ip_is_public(ip_str: str) -> bool:
    """True iff ``ip_str`` is a routable public address.

    Rejects private, loopback, link-local (169.254/16 cloud metadata),
    reserved, multicast and unspecified addresses, in both IPv4 and IPv6.
    Raises ``ValueError`` if ``ip_str`` is not a valid address literal.
    """
    ip = ipaddress.ip_address(ip_str)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _resolve_public_addresses(host: str, port: int) -> list[tuple[int, str]]:
    """Resolve ``host`` ONCE and return its ``[(family, ip), ...]``.

    Raises ``ValueError`` if the host does not resolve or if ANY resolved
    address is non-public. This single resolution is the anchor of the
    anti-rebinding guarantee: the addresses returned here are exactly the ones
    the caller pins the socket to, so the address that is *validated* is the
    address that is *connected*.
    """
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ValueError(f"host {host!r} does not resolve: {exc}") from exc
    if not infos:
        raise ValueError(f"host {host!r} does not resolve")
    addresses: list[tuple[int, str]] = []
    for info in infos:
        family, ip_str = info[0], info[4][0]
        try:
            public = _ip_is_public(ip_str)
        except ValueError as exc:
            raise ValueError(f"unparseable resolved address {ip_str!r}") from exc
        if not public:
            raise ValueError(
                f"host {host!r} resolves to non-public address {ip_str}"
            )
        addresses.append((family, ip_str))
    return addresses


def is_safe_public_url(url: str) -> tuple[bool, str]:
    """Return ``(True, "")`` if ``url`` targets a PUBLIC host, else ``(False, reason)``.

    Rejects non-http(s) schemes and any host that resolves to a private,
    loopback, link-local, reserved, multicast, or unspecified address — which
    covers 127.0.0.0/8, 169.254.0.0/16 (cloud metadata), RFC1918, ::1 and
    fc00::/7. Resolution is done here (not left to requests) so the decision is
    made on the real destination IP, defeating hostname tricks.

    NOTE: this is a point-in-time *check*. Because ``requests`` re-resolves when
    it connects, code that actually FETCHES must use :func:`fetch_public_url`
    (which pins the vetted IP for the connection) — validating here and then
    fetching by hostname is vulnerable to DNS rebinding.
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
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        return False, f"invalid port: {exc}"
    try:
        _resolve_public_addresses(host, port)
    except ValueError as exc:
        return False, str(exc)
    return True, ""


def _pinned_ip_adapter(pinned_ip: str, *, connector=None):
    """Build a requests ``HTTPAdapter`` that forces the TCP connection to
    ``pinned_ip`` while keeping the original hostname for everything else.

    The socket is opened to ``pinned_ip`` (an already-vetted IP literal, so its
    own ``getaddrinfo`` is a no-op numeric lookup — no DNS, hence nothing to
    rebind), but the connection's ``host`` is left untouched, so the ``Host``
    header, TLS SNI, and the certificate-hostname check all still use the real
    hostname and ordinary HTTPS keeps working.

    Implementation: override each connection's ``_new_conn`` (the low-level
    socket factory) rather than its ``host`` / ``_dns_host`` — in urllib3 2.x
    ``host`` is a property backed by ``_dns_host``, so rewriting ``_dns_host``
    would also corrupt the Host header and SNI. ``requests`` / ``urllib3`` are
    imported lazily so :func:`is_safe_public_url` stays usable with only the
    stdlib.
    """
    from requests.adapters import HTTPAdapter
    from urllib3.util import connection as _u3conn

    def _guarded_new_conn(conn):
        # Zero-arg replacement for HTTPConnection._new_conn: connect to the
        # vetted IP, keep conn.host (Host header / SNI / cert) as the hostname.
        def _new_conn():
            # A literal IP means the socket layer performs no hostname DNS here,
            # so there is nothing left to rebind. ``connector`` is a test seam
            # (dependency injection); production uses urllib3's connector.
            connect = connector if connector is not None else _u3conn.create_connection
            return connect(
                (pinned_ip, conn.port),
                conn.timeout,
                source_address=conn.source_address,
                socket_options=conn.socket_options,
            )

        return _new_conn

    class _PinnedIPAdapter(HTTPAdapter):
        def _pin(self, pool):
            # Wrap the pool's connection factory so every connection it opens is
            # pinned. Guard against re-wrapping the same pool twice.
            if getattr(pool, "_ssrf_pinned", False):
                return pool
            original_new_conn = pool._new_conn

            def _pool_new_conn():
                conn = original_new_conn()
                conn._new_conn = _guarded_new_conn(conn)
                return conn

            pool._new_conn = _pool_new_conn
            pool._ssrf_pinned = True
            return pool

        # requests >= 2.32
        def get_connection_with_tls_context(
            self, request, verify, proxies=None, cert=None
        ):
            pool = super().get_connection_with_tls_context(
                request, verify, proxies=proxies, cert=cert
            )
            return self._pin(pool)

        # requests < 2.32 fallback
        def get_connection(self, url, proxies=None):  # pragma: no cover
            pool = super().get_connection(url, proxies=proxies)
            return self._pin(pool)

    return _PinnedIPAdapter()


def fetch_public_url(
    url,
    *,
    timeout=_DEFAULT_TIMEOUT,
    headers=None,
    max_redirects=_MAX_REDIRECTS,
    _resolver=None,
    _connector=None,
):
    """GET ``url``, following redirects, with SSRF protection on every hop.

    For each hop the host is resolved ONCE, every resolved address must be
    public, and the connection is PINNED to a vetted address so
    ``requests``/``urllib3`` cannot re-resolve to an internal host between the
    check and the connect (DNS-rebinding defence). Redirects are followed
    manually so each ``Location`` is validated and pinned the same way.

    Raises ``ValueError`` on a blocked / unresolvable host, a non-http(s)
    scheme, a redirect without a ``Location``, or too many redirects. Returns a
    streaming ``requests.Response`` for the final hop; the ``requests.Session``
    owning the live connection is attached to the response so it outlives this
    call and the body can be streamed by the caller.

    ``_resolver`` and ``_connector`` are dependency-injection seams for tests
    (the host resolver and the socket connector); production uses the module
    default resolver and urllib3's connector.
    """
    import requests  # lazy: keeps the validator stdlib-only

    resolve = _resolver if _resolver is not None else _resolve_public_addresses

    current = url
    for _ in range(max_redirects + 1):
        parsed = urlparse(current)
        if parsed.scheme not in _ALLOWED_SCHEMES:
            raise ValueError(
                "blocked URL (SSRF protection): scheme "
                f"{parsed.scheme!r} not allowed (http/https only)"
            )
        host = parsed.hostname
        if not host:
            raise ValueError("blocked URL (SSRF protection): URL has no host")
        try:
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except ValueError as exc:
            raise ValueError(
                f"blocked URL (SSRF protection): invalid port: {exc}"
            ) from exc

        try:
            addresses = resolve(host, port)
        except ValueError as exc:
            raise ValueError(f"blocked URL (SSRF protection): {exc}") from exc
        pinned_ip = addresses[0][1]

        session = requests.Session()
        session.mount(
            f"{parsed.scheme}://",
            _pinned_ip_adapter(pinned_ip, connector=_connector),
        )
        resp = session.get(
            current,
            timeout=timeout,
            stream=True,
            allow_redirects=False,
            headers=headers,
        )
        if resp.is_redirect or resp.is_permanent_redirect:
            location = resp.headers.get("Location")
            resp.close()
            session.close()
            if not location:
                raise ValueError("redirect without a Location header")
            current = urljoin(current, location)
            continue
        # Keep the session (and thus the checked-out pooled connection) alive so
        # the caller can stream the body after this function returns.
        resp._ssrf_session = session
        return resp
    raise ValueError("too many redirects")
