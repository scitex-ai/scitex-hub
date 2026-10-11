#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Network-only jail for Scholar Slice 1 (stateless proxy).

Card hub-figrecipe-leaf-move-20261009, Slice 1: the citation-graph AllowAny
endpoints + the crossref/search proxy run behind an egress jail. No DB, no
files — the only thing caller input can influence here is *which public
papers we fetch*, never *where we connect to*.

What the jail enforces (fail-closed, ``EgressDenied``):
- PUBLIC egress (``jailed_get``): the URL host must be exactly one of
  ``PUBLIC_EGRESS_HOSTS`` (case-insensitive, no userinfo, no literal-IP
  host, no explicit port). Caller-controlled values (DOI, query, limit)
  travel as query *params* only — they can never become the host, scheme,
  or path of the request.
- INTERNAL egress (``jailed_get_internal`` + ``build_internal_url``): for
  server-configured bases only (crossref-local ``CROSSREF_INTERNAL_URL``,
  citation-graph NAS proxy base from env/settings). The base host comes
  from server config, never from the request; per-call path segments are
  joined by ``build_internal_url``, which refuses absolute URLs, schemes,
  and ``//host`` forms. Docker DNS names / loopback are allowed here
  because the operator configures them — the guarantee is provenance
  (server-side), not publicity.
- BOUNDS (both): timeout clamped to (0, ``MAX_TIMEOUT_S``] (default 60;
  the search views' 180s stays legal, anything above is clamped, never
  extended); response bodies capped at ``MAX_BODY_BYTES`` (8 MiB, same
  ceiling as the FigRecipe container proxy) via Content-Length pre-check
  + streamed cap. ``EgressDenied`` subclasses
  ``requests.exceptions.RequestException`` so existing handlers keep
  their 503/empty-list shapes.

Auth review — the 10 AllowAny routes in this slice (per-route, 2026-10-11):
- citation_graph.build_network / build_network_multi / build_network_query /
  get_related_papers: AllowAny + CitationGraphThrottle (50/hour). STAYS PUBLIC.
- citation_graph.health: AllowAny + HealthCheckThrottle (10/min). STAYS PUBLIC.
- citation_graph.paper_summary: was AllowAny with NO throttle ("simple
  lookup"). Now AllowAny + CitationGraphThrottle (50/hour) — same bucket
  semantics as its siblings. STAYS PUBLIC, throttled (behavior change only
  under flood: 429 past the window instead of unbounded 200s).
- crossref_proxy.search / citations: AllowAny + CrossRefAPIThrottle
  (100/hour). STAYS PUBLIC.
- crossref_proxy.health / stats: were AllowAny with NO throttle. Now
  AllowAny + PublicHealthThrottle (10/min). STAYS PUBLIC, throttled
  (same flood-only behavior note; these fan out to the internal service,
  so unthrottled anon access was an amplification vector).
- public v1 search/info (``public_search``): anon rate_limit decorator
  (10/min) + API-key tiers. UNCHANGED, already throttled-public.

SDK reference: scitex-sdk PR #49 (``scitex_sdk/app/jail.py``,
``validate_mount_policy`` + ``is_in_jail``/``resolve_against``/
``first_escape``) is the enforcement *contract* this mirrors, but it is
unmerged and its primitives are filesystem-oriented (mount_policy jail).
The network half has no SDK counterpart yet, so this module implements
the network-only side hub-side, defensively, in the same fail-closed
shape: allowlisted destinations, caller input never becomes a location,
loud denial. When the SDK ships a network jail, these call sites adopt
it (same function names by design: ``jailed_get*``).

No caller-controlled path reaches the filesystem: this module performs
zero file I/O, and every egress call site in the slice routes through
it (pinned by ``test_slice1_network_jail.py::test_no_raw_egress``).
"""

from __future__ import annotations

import io
import ipaddress
from urllib.parse import urlparse

import requests

#: Public paper-metadata hosts the search/graph proxy may contact.
#: Exact-match only (no subdomain wildcard, no suffix match).
PUBLIC_EGRESS_HOSTS = frozenset(
    {
        "api.crossref.org",
        "api.openalex.org",
        "api.semanticscholar.org",
        "eutils.ncbi.nlm.nih.gov",
        "export.arxiv.org",
        "doaj.org",
        "api.biorxiv.org",
        "api.plos.org",
    }
)

#: Upper bound for any outbound read. The search views' 180s stays legal.
MAX_TIMEOUT_S = 180
DEFAULT_TIMEOUT_S = 60

#: Response body ceiling (mirrors the FigRecipe container-proxy 8 MiB cap).
MAX_BODY_BYTES = 8 * 1024 * 1024

_CHUNK = 64 * 1024


class EgressDenied(requests.exceptions.RequestException):
    """Fail-closed denial from the network jail.

    Subclasses ``RequestException`` deliberately: every call site in this
    slice already maps that to its degraded shape (503 JSON / empty list /
    online-fallback), so a denied request degrades exactly like a down
    upstream instead of surfacing a 500.
    """


def _hostname(url: str) -> str:
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise EgressDenied(f"refusing unparseable URL: {url!r}") from exc
    if parsed.scheme not in ("http", "https"):
        raise EgressDenied(f"refusing non-http(s) URL: {url!r}")
    if parsed.username or parsed.password:
        raise EgressDenied(f"refusing URL with credentials: {parsed.hostname!r}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise EgressDenied(f"refusing URL without host: {url!r}")
    return host


def assert_public_url(url: str) -> str:
    """Validate a public-egress URL; return the hostname or raise."""
    host = _hostname(url)
    parsed = urlparse(url)
    if host not in PUBLIC_EGRESS_HOSTS:
        raise EgressDenied(f"egress host not allowlisted: {host!r}")
    if parsed.port is not None:
        raise EgressDenied(f"refusing explicit port on public egress: {url!r}")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        # A literal IP can never be an allowlisted DNS name (exact match
        # above already failed for it), but reject explicitly so the
        # reason is legible rather than a generic allowlist miss.
        raise EgressDenied(f"refusing literal-IP public egress: {host!r}")
    return host


def build_internal_url(base: str, *parts: str, trailing_slash: bool = True) -> str:
    """Join server-configured ``base`` with fixed path ``parts``.

    ``base`` must come from server config (env/settings), never from the
    request. ``parts`` are per-method literals. Anything shaped like an
    absolute URL, a scheme, or a ``//host`` override is refused — a
    caller-controlled segment can never redirect the request elsewhere.
    ``trailing_slash`` preserves each upstream's exact path shape.
    """
    base_host = _hostname(base)
    if not base_host:
        raise EgressDenied(f"refusing internal base without host: {base!r}")
    for part in parts:
        if not part or not isinstance(part, str):
            raise EgressDenied(f"refusing empty internal path segment: {part!r}")
        stripped = part.strip()
        if (
            "://" in stripped
            or stripped.startswith("//")
            or stripped.startswith("\\\\")
            or urlparse(stripped).scheme
        ):
            raise EgressDenied(f"refusing absolute internal path: {part!r}")
        if "\\" in stripped:
            raise EgressDenied(f"refusing backslash internal path: {part!r}")
    url = base.rstrip("/") + "/" + "/".join(p.strip("/") for p in parts)
    if trailing_slash:
        url += "/"
    # Re-parse: the join must not have smuggled in a new authority.
    if (urlparse(url).hostname or "").lower() != base_host:
        raise EgressDenied(f"internal join escaped its base host: {url!r}")
    return url


def _clamp_timeout(timeout: float | int | None) -> float:
    if timeout is None:
        return float(DEFAULT_TIMEOUT_S)
    try:
        value = float(timeout)
    except (TypeError, ValueError) as exc:
        raise EgressDenied(f"refusing non-numeric timeout: {timeout!r}") from exc
    if value <= 0:
        raise EgressDenied(f"refusing non-positive timeout: {timeout!r}")
    return min(value, float(MAX_TIMEOUT_S))


def _read_capped(response: requests.Response, max_bytes: int) -> bytes:
    """Populate ``response._content`` under a byte ceiling (fail-closed)."""
    if max_bytes <= 0:
        raise EgressDenied(f"refusing non-positive body cap: {max_bytes!r}")
    length = response.headers.get("Content-Length")
    if length is not None:
        try:
            if int(length) > max_bytes:
                raise EgressDenied(
                    f"refusing {length}B body over {max_bytes}B cap "
                    f"from {response.url!r}"
                )
        except ValueError:
            pass  # unparseable length: fall through to the streamed cap
    buf = io.BytesIO()
    total = 0
    for chunk in response.raw.stream(_CHUNK, decode_content=True):
        total += len(chunk)
        if total > max_bytes:
            raise EgressDenied(
                f"refusing streamed body over {max_bytes}B cap "
                f"from {response.url!r}"
            )
        buf.write(chunk)
    return buf.getvalue()


def _capped_get(
    url: str,
    *,
    params=None,
    headers=None,
    timeout=None,
    max_bytes: int = MAX_BODY_BYTES,
) -> requests.Response:
    clamped = _clamp_timeout(timeout)
    with requests.get(
        url, params=params, headers=headers, timeout=clamped, stream=True
    ) as response:
        response._content = _read_capped(response, max_bytes)
        return response


def jailed_get(
    url: str,
    *,
    params=None,
    headers=None,
    timeout: float | int | None = None,
    max_bytes: int = MAX_BODY_BYTES,
) -> requests.Response:
    """GET a public paper-metadata URL behind the egress allowlist."""
    assert_public_url(url)
    return _capped_get(
        url, params=params, headers=headers, timeout=timeout, max_bytes=max_bytes
    )


def jailed_get_internal(
    url: str,
    *,
    params=None,
    headers=None,
    timeout: float | int | None = None,
    max_bytes: int = MAX_BODY_BYTES,
) -> requests.Response:
    """GET a server-configured internal URL (crossref-local / NAS proxy).

    ``url`` must be built via ``build_internal_url`` from a configured
    base — this function re-checks shape (http(s), no credentials) and
    applies the same timeout/body bounds as public egress, but allows
    operator-configured hosts (docker DNS names, loopback) that the
    public allowlist would refuse.
    """
    host = _hostname(url)
    if not host:
        raise EgressDenied(f"refusing internal URL without host: {url!r}")
    return _capped_get(
        url, params=params, headers=headers, timeout=timeout, max_bytes=max_bytes
    )


# EOF
