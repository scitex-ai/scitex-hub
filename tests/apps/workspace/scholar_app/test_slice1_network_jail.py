#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar Slice 1: stateless proxy behind the network-only jail.

Card hub-figrecipe-leaf-move-20261009 (Slice 1): citation-graph AllowAny
endpoints + crossref/search proxy run behind
``apps.workspace.scholar_app.services.network_jail``. No DB, no files.

Three-sided on purpose:
1. JAIL UNIT — allowlisted hosts pass with clamped timeouts and capped
   bodies; everything else (foreign hosts, subdomain tricks, userinfo,
   literal IPs, explicit public ports, non-http schemes, absolute
   internal paths) fails closed with ``EgressDenied``.
2. WIRING GATE (AST) — each of the 10 AllowAny routes carries
   permission_classes (AllowAny, reviewed per route — see the jail
   module docstring) + throttle_classes, and no raw ``requests.get``
   remains in the slice files, so a future edit cannot silently bypass
   the jail.
3. BEHAVIOR PARITY — anonymous validation-error shapes, error
   degradations (503/empty), and public-search responses are byte-equal
   in shape to the pre-slice hub behavior (mocked egress only; no
   network, no DB).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import requests as _requests

import apps.workspace.scholar_app.services.network_jail as jail
from apps.workspace.scholar_app.services.network_jail import (
    EgressDenied,
    build_internal_url,
    jailed_get,
    jailed_get_internal,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHOLAR = REPO_ROOT / "apps" / "workspace" / "scholar_app"

# Files whose egress belongs to Slice 1 (stateless only). Repository/DOI
# egress (services/repository/*) is Slice 4 and intentionally excluded.
SLICE_FILES = [
    "api/citation_graph.py",
    "api/crossref_proxy.py",
    "api/public_search.py",
    "api/public_search_utils.py",
    "services/citation_graph/online.py",
    "services/citation_graph/proxy.py",
    "services/network_jail.py",
    "views/search/api_crossref.py",
    "views/search/api_openalex.py",
    "views/search/engines/arxiv.py",
    "views/search/engines/openaccess.py",
    "views/search/engines/pubmed.py",
    "views/search/engines/pubmed_central.py",
    "views/search/engines/semantic.py",
    "views/workspace/api_key_views.py",
]

# The 10 reviewed AllowAny routes: (module file, view function name).
ALLOW_ANY_ROUTES = [
    ("api/citation_graph.py", "build_network"),
    ("api/citation_graph.py", "build_network_multi"),
    ("api/citation_graph.py", "build_network_query"),
    ("api/citation_graph.py", "get_related_papers"),
    ("api/citation_graph.py", "paper_summary"),
    ("api/citation_graph.py", "health"),
    ("api/crossref_proxy.py", "search"),
    ("api/crossref_proxy.py", "citations"),
    ("api/crossref_proxy.py", "health"),
    ("api/crossref_proxy.py", "stats"),
]


# ---------------------------------------------------------------------------
# Fake transport
# ---------------------------------------------------------------------------


class _FakeRaw:
    def __init__(self, body: bytes):
        self._body = body

    def stream(self, chunk_size, decode_content=True):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i : i + chunk_size]


class _FakeResponse:
    """Minimal requests.Response double supporting the jail protocol."""

    def __init__(self, body: bytes = b'{"ok": true}', headers=None, url=""):
        self._body = body
        self.headers = headers or {}
        self.url = url
        self.status_code = 200
        self.raw = _FakeRaw(body)
        self._content = False  # requests uses False until content is read

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise _requests.exceptions.HTTPError(f"{self.status_code}")

    def json(self):
        import json

        content = self._content if self._content is not False else self._body
        return json.loads(content.decode())


@pytest.fixture
def capture(monkeypatch):
    """Capture jailed transport args; serve a canned body."""
    seen = {}

    def fake_get(url, params=None, headers=None, timeout=None, stream=False):
        seen.update(
            url=url, params=params, headers=headers, timeout=timeout, stream=stream
        )
        body = fake_get.body
        resp = _FakeResponse(
            body=body,
            headers={"Content-Length": str(len(body))},
            url=url,
        )
        return resp

    fake_get.body = b'{"ok": true}'
    fake_get.seen = seen
    monkeypatch.setattr(jail.requests, "get", fake_get)
    return fake_get


# ---------------------------------------------------------------------------
# 1. Jail unit
# ---------------------------------------------------------------------------


def test_allowlisted_hosts_pass(capture):
    for host in sorted(jail.PUBLIC_EGRESS_HOSTS):
        resp = jailed_get(f"https://{host}/works", params={"q": "x"}, timeout=60)
        assert capture.seen["url"] == f"https://{host}/works"
        assert resp.json() == {"ok": True}


def test_subdomain_trick_denied(capture):
    with pytest.raises(EgressDenied):
        jailed_get("https://api.crossref.org.evil.example/works")


def test_foreign_host_denied(capture):
    with pytest.raises(EgressDenied):
        jailed_get("https://169.254.169.254/latest/meta-data/")
    with pytest.raises(EgressDenied):
        jailed_get("https://example.com/works")


def test_userinfo_literal_ip_port_scheme_denied(capture):
    with pytest.raises(EgressDenied):
        jailed_get("https://user:pass@api.crossref.org/works")
    with pytest.raises(EgressDenied):
        jailed_get("https://127.0.0.1/works")
    with pytest.raises(EgressDenied):
        jailed_get("https://api.crossref.org:8443/works")
    with pytest.raises(EgressDenied):
        jailed_get("ftp://api.crossref.org/works")


def test_case_insensitive_host_allowed(capture):
    resp = jailed_get("https://API.CROSSREF.ORG/works")
    assert resp.json() == {"ok": True}


def test_timeout_clamped_not_extended(capture):
    jailed_get("https://api.crossref.org/works", timeout=999)
    assert capture.seen["timeout"] == float(jail.MAX_TIMEOUT_S)
    jailed_get("https://api.crossref.org/works", timeout=None)
    assert capture.seen["timeout"] == float(jail.DEFAULT_TIMEOUT_S)


def test_timeout_non_positive_denied(capture):
    with pytest.raises(EgressDenied):
        jailed_get("https://api.crossref.org/works", timeout=0)
    with pytest.raises(EgressDenied):
        jailed_get("https://api.crossref.org/works", timeout=-5)


def test_body_cap_content_length_precheck(capture):
    capture.body = b"x" * 10
    with pytest.raises(EgressDenied):
        jailed_get("https://api.crossref.org/works", max_bytes=9)
    # Nothing may have been streamed: the denial happens on headers.
    assert capture.seen["stream"] is True


def test_body_cap_streamed_overflow(monkeypatch):
    # Lying (or absent) Content-Length must not bypass the cap.
    body = b"y" * 100

    def fake_get(url, params=None, headers=None, timeout=None, stream=False):
        return _FakeResponse(body=body, headers={}, url=url)

    monkeypatch.setattr(jail.requests, "get", fake_get)
    with pytest.raises(EgressDenied):
        jailed_get("https://api.crossref.org/works", max_bytes=10)


def test_denial_is_a_request_exception():
    assert issubclass(EgressDenied, _requests.exceptions.RequestException)


def test_build_internal_url_shapes():
    assert (
        build_internal_url("http://crossref:31291", "api", "search")
        == "http://crossref:31291/api/search/"
    )
    assert (
        build_internal_url("http://crossref:31291/", "health", trailing_slash=False)
        == "http://crossref:31291/health"
    )
    assert (
        build_internal_url("https://scitex.ai", "api", "scholar", "citation-graph", "x")
        == "https://scitex.ai/api/scholar/citation-graph/x/"
    )


def test_build_internal_url_refuses_escape():
    base = "http://crossref:31291"
    for bad in (
        "https://evil.example/x",
        "//evil.example/x",
        "http://evil.example/",
        "..\\evil",
        "",
    ):
        with pytest.raises(EgressDenied):
            build_internal_url(base, bad)


def test_internal_allows_operator_hosts_but_not_credentials(capture):
    resp = jailed_get_internal("http://crossref:31291/api/search/", timeout=60)
    assert resp.json() == {"ok": True}
    resp = jailed_get_internal("http://127.0.0.1:31291/health", timeout=5)
    assert resp.json() == {"ok": True}
    with pytest.raises(EgressDenied):
        jailed_get_internal("http://user:pw@crossref:31291/api/search/")


# ---------------------------------------------------------------------------
# 2. Wiring gates (AST — no DRF internals, no network)
# ---------------------------------------------------------------------------


def _decorators(path: Path, func: str) -> list[str]:
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func:
                out = []
                for dec in node.decorator_list:
                    try:
                        out.append(ast.unparse(dec))
                    except Exception:
                        out.append(getattr(dec, "attr", getattr(dec, "id", "")))
                return out
    raise AssertionError(f"{func} not found in {path}")


def test_ten_allow_any_routes_carry_auth_and_throttle():
    """Per-route review gate: every public route keeps AllowAny AND a
    throttle. If a future edit drops either decorator, this names the
    route instead of silently widening (or narrowing) the surface."""
    assert len(ALLOW_ANY_ROUTES) == 10
    for rel, func in ALLOW_ANY_ROUTES:
        decs = _decorators(SCHOLAR / rel, func)
        assert any(
            d.startswith("permission_classes") and "AllowAny" in d for d in decs
        ), f"{rel}:{func} lost its AllowAny gate"
        assert any(d.startswith("throttle_classes") for d in decs), (
            f"{rel}:{func} has no throttle — public without "
            "throttled-public proof (login-gate it or throttle it)"
        )


def test_no_raw_egress_in_slice():
    """Every outbound call in the slice routes through the jail, so no
    caller-controlled value can reach the transport directly."""
    offenders = []
    for rel in SLICE_FILES:
        path = SCHOLAR / rel
        assert path.exists(), f"slice file moved without updating the gate: {rel}"
        if path.name == "network_jail.py":
            continue  # the jail IS the single transport chokepoint
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in (
                "get",
                "post",
                "put",
                "request",
            ):
                value = node.value
                if isinstance(value, ast.Name) and value.id == "requests":
                    offenders.append(f"{rel}:{node.lineno}")
    assert not offenders, f"raw requests egress bypassing the jail: {offenders}"


def test_slice_performs_no_file_io():
    """Slice 1 is stateless: the jail itself must never touch the FS."""
    tree = ast.parse((SCHOLAR / "services" / "network_jail.py").read_text())
    banned = {"open"}
    hits = [
        f"{node.lineno}:{node.func.id}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in banned
    ]
    assert not hits, f"file I/O in the stateless jail: {hits}"


# ---------------------------------------------------------------------------
# 3. Behavior parity (mocked egress only)
# ---------------------------------------------------------------------------


@pytest.fixture
def api_factory():
    from rest_framework.test import APIRequestFactory

    return APIRequestFactory()


@pytest.fixture(autouse=True)
def _locmem_cache(settings):
    """Throttle/rate-limit paths need a working cache; the dev settings
    fall back to DatabaseCache here (no Redis, no DB), so pin locmem
    for this module. Parity assertions never depend on cached values."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "slice1-test",
        }
    }
    from django.core.cache import cache

    cache.clear()


def test_citation_graph_validation_shapes(api_factory):
    from apps.workspace.scholar_app.api import citation_graph as cg

    cases = [
        (cg.build_network, "/api/scholar/citation-graph/network/", {}),
        (cg.build_network_multi, "/api/scholar/citation-graph/network/multi/", {}),
        (cg.build_network_query, "/api/scholar/citation-graph/network/query/", {}),
        (cg.get_related_papers, "/api/scholar/citation-graph/related/", {}),
        (cg.paper_summary, "/api/scholar/citation-graph/paper/", {}),
    ]
    for view, url, params in cases:
        resp = view(api_factory.get(url, params))
        # Anonymous passes auth (AllowAny) and fails on validation, never 403.
        assert resp.status_code == 400, (url, resp.status_code)
        assert "error" in resp.data, url

    resp = cg.build_network(api_factory.get("/x/", {"doi": "10.1/y", "top_n": "99"}))
    assert resp.status_code == 400
    assert resp.data == {"error": "top_n must be between 1 and 50"}


def test_citation_graph_upstream_shapes_with_stub_service(api_factory, monkeypatch):
    """Hub-served response shapes with the backend stubbed (parity: the
    jail changes transport, never the contract)."""
    import apps.workspace.scholar_app.api.citation_graph as cg

    network = {
        "seed": "10.1/y",
        "nodes": [{"id": "10.1/y"}],
        "edges": [],
        "metadata": {"top_n": 20},
    }

    class Stub:
        def build_network(self, **kwargs):
            return dict(network)

        def build_network_from_dois(self, **kwargs):
            return dict(network)

        def build_network_from_query(self, **kwargs):
            return dict(network)

        def get_related_papers(self, **kwargs):
            return [{"id": "10.1/z"}]

        def get_paper_summary(self, doi):
            return {"doi": doi, "title": "T"}

    monkeypatch.setattr(cg, "get_citation_graph_service", lambda: Stub())

    resp = cg.build_network(api_factory.get("/x/", {"doi": "10.1/y"}))
    assert resp.status_code == 200
    assert resp.data["seed"] == "10.1/y"

    resp = cg.get_related_papers(api_factory.get("/x/", {"doi": "10.1/y"}))
    assert resp.status_code == 200
    assert resp.data == {"doi": "10.1/y", "related": [{"id": "10.1/z"}], "count": 1}

    resp = cg.paper_summary(api_factory.get("/x/", {"doi": "10.1/y"}))
    assert resp.status_code == 200
    assert resp.data["title"] == "T"


def test_crossref_proxy_validation_and_degraded_shapes(api_factory, monkeypatch):
    from apps.workspace.scholar_app.api import crossref_proxy as cp

    # NOTE (parity, not a fix): search/ defaults limit=10, so ``params``
    # is never empty and the "At least one search parameter" 400 is
    # unreachable — a bare call proxies upstream. This slice preserves
    # that quirk exactly; changing it belongs to a behavior PR, not Slice 1.
    def boom(*args, **kwargs):
        raise _requests.exceptions.ConnectionError("down")

    import apps.workspace.scholar_app.services.network_jail as jail_mod

    monkeypatch.setattr(jail_mod.requests, "get", boom)
    resp = cp.search(api_factory.get("/x/"))
    assert resp.status_code == 503
    assert "error" in resp.data

    resp = cp.citations(api_factory.get("/x/"))
    assert resp.status_code == 400
    assert resp.data == {"error": "DOI parameter required"}

    resp = cp.citations(api_factory.get("/x/", {"doi": "10.1/y", "depth": "9"}))
    assert resp.status_code == 400
    assert resp.data == {"error": "Maximum depth is 3"}

    # Degraded (downstream down) keeps the 503 JSON shape through the jail.
    resp = cp.health(api_factory.get("/x/"))
    assert resp.status_code == 503
    assert resp.data["public_api"] == "unhealthy"
    resp = cp.stats(api_factory.get("/x/"))
    assert resp.status_code == 503
    assert "error" in resp.data


def test_public_search_parity(api_factory):
    from apps.workspace.scholar_app.api import public_search as ps

    resp = ps.info(api_factory.get("/x/"))
    assert resp.status_code == 200
    import json

    body = json.loads(resp.content)
    assert body["api_version"] == "v1"
    assert body["status"] == "ok"

    from django.test import RequestFactory

    req = RequestFactory().get("/api/v1/scholar/search/")
    resp = ps.search(req)
    assert resp.status_code == 400
    import json as _json

    assert "error" in _json.loads(resp.content)


def test_online_source_uses_jailed_transport(monkeypatch):
    """The Crossref-online graph path cannot be pointed at a foreign host:
    even a poisoned module constant is stopped by the allowlist."""
    import apps.workspace.scholar_app.services.citation_graph.online as online

    seen = {}
    real_assert = jail.assert_public_url

    class Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"items": []}}

    def fake_jailed(url, params=None, headers=None, timeout=None, max_bytes=None):
        # The double serves bytes but NEVER the allowlist decision: the
        # real assertion runs first, so a poisoned constant still denies.
        real_assert(url)
        seen["url"] = url
        return Resp()

    monkeypatch.setattr(online, "jailed_get", fake_jailed)
    src = online.OnlineCrossrefGraphSource()
    assert src.build_from_dois(["10.1/y"])["metadata"]["source"] == "crossref_online"
    assert seen["url"] == online.CROSSREF_WORKS

    monkeypatch.setattr(online, "CROSSREF_WORKS", "https://evil.example/works")
    with pytest.raises(EgressDenied):
        src.build_from_dois(["10.1/y"])


# EOF
