#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Container proxy: gating, header hygiene, per-user routing, fallback.

Card hub-figrecipe-leaf-move-20261009 (Apptainer pilot). No container, no
DB, no credentials: HTTP is faked, tokens are stubbed. Pins the boundary
contract — cookies never cross it, the HMAC token always does, failures
fall back in-process, and the SITE-2 guard file is untouched by the slice.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.test import RequestFactory

from apps.workspace.figrecipe_app.services import container_proxy as proxy


def _authed_request(path="/apps/figrecipe/", user="alice"):
    rf = RequestFactory()
    request = rf.get(path, HTTP_COOKIE="sessionid=abc", HTTP_AUTHORIZATION="Bearer x")
    request.user = SimpleNamespace(
        username=user, pk=7, is_authenticated=True, is_anonymous=False
    )
    return request


def test_disabled_without_url_and_secret(monkeypatch):
    # Arrange
    monkeypatch.delenv(proxy.URL_ENV, raising=False)
    monkeypatch.delenv(proxy.KEY_ENV, raising=False)
    # Act / Assert
    assert proxy.enabled() is False


def test_disabled_without_secret(monkeypatch):
    # Arrange
    monkeypatch.setenv(proxy.URL_ENV, "http://127.0.0.1:18096")
    monkeypatch.delenv(proxy.KEY_ENV, raising=False)
    # Act / Assert — fail-safe: no secret means in-process, never unsigned
    assert proxy.enabled() is False


def test_enabled_with_url_and_secret(monkeypatch):
    # Arrange
    monkeypatch.setenv(proxy.URL_ENV, "http://127.0.0.1:18096")
    monkeypatch.setenv(proxy.KEY_ENV, "k")
    # Act / Assert
    assert proxy.enabled() is True


def test_proxy_strips_cookies_and_injects_token(monkeypatch):
    # Arrange — fake the transport, stub the token
    monkeypatch.setenv(proxy.URL_ENV, "http://127.0.0.1:18096")
    monkeypatch.setenv(proxy.KEY_ENV, "k")
    monkeypatch.setenv(proxy.ALLOW_SHARED_ENV, "1")
    seen = {}

    class _Resp:
        status = 200

        def getheader(self, name, default=None):
            return "text/html"

        def read(self, *a):
            return b"<html>container</html>"

    class _Conn:
        def __init__(self, host, port=None, timeout=None):
            seen["host"], seen["port"] = host, port

        def request(self, method, target, body=None, headers=None):
            seen["method"], seen["target"], seen["headers"] = method, target, headers

        def getresponse(self):
            return _Resp()

        def close(self):
            seen["closed"] = True

    monkeypatch.setattr(proxy.http.client, "HTTPConnection", _Conn)
    monkeypatch.setattr(proxy, "mint_token_for", lambda request: "TOKEN-123")
    # Act
    response = proxy.proxy_request(_authed_request(), "")
    # Assert — token in, cookies/auth out, connection closed
    headers = {k.lower(): v for k, v in seen["headers"].items()}
    assert headers["x-figrecipe-auth"] == "TOKEN-123"
    assert "cookie" not in headers and "authorization" not in headers
    assert seen["closed"] is True
    assert response.status_code == 200
    assert b"container" in response.content


def test_proxy_routes_mapped_user_to_per_uid_port(monkeypatch):
    # Arrange — alice maps to a uid; her container lives on her own port
    monkeypatch.setenv(proxy.URL_ENV, "http://127.0.0.1:18096")
    monkeypatch.setenv(proxy.KEY_ENV, "k")
    monkeypatch.setenv("FIGRECIPE_UID_MAP", "alice:10001")
    from apps.workspace.figrecipe_app.services import container_spawner as spawner

    expect_port = spawner.user_port(10001)
    seen = {}

    class _Resp:
        status = 200

        def getheader(self, name, default=None):
            return "text/html"

        def read(self, *a):
            return b"ok"

    class _Conn:
        def __init__(self, host, port=None, timeout=None):
            seen["host"], seen["port"] = host, port

        def request(self, method, target, body=None, headers=None):
            pass

        def getresponse(self):
            return _Resp()

        def close(self):
            pass

    monkeypatch.setattr(proxy.http.client, "HTTPConnection", _Conn)
    monkeypatch.setattr(proxy, "mint_token_for", lambda request: "T")
    # Act
    proxy.proxy_request(_authed_request(user="alice"), "")
    # Assert — loopback host, per-uid port (not the shared default)
    assert seen["host"] == "127.0.0.1"
    assert seen["port"] == expect_port


def test_proxy_falls_back_when_container_down(monkeypatch):
    # Arrange — nothing listens; transport raises
    monkeypatch.setenv(proxy.URL_ENV, "http://127.0.0.1:18096")
    monkeypatch.setenv(proxy.KEY_ENV, "k")
    monkeypatch.setenv(proxy.ALLOW_SHARED_ENV, "1")
    monkeypatch.setattr(proxy, "mint_token_for", lambda request: "T")

    class _Down:
        def __init__(self, *a, **k):
            raise ConnectionRefusedError("down")

    monkeypatch.setattr(proxy.http.client, "HTTPConnection", _Down)
    # Act / Assert
    with pytest.raises(proxy.ContainerUnavailable):
        proxy.proxy_request(_authed_request(), "")


def test_bad_container_url_fails_closed(monkeypatch):
    # Arrange
    monkeypatch.setenv(proxy.URL_ENV, "not-a-url")
    monkeypatch.setenv(proxy.KEY_ENV, "k")
    # Act / Assert
    with pytest.raises(proxy.ContainerUnavailable):
        proxy.proxy_request(_authed_request(), "", token="T")


def test_jail_guard_module_untouched():
    # Arrange — the slice must not thin SITE-2 until containment is proven
    # Act
    import apps.workspace.figrecipe_app.urls.figrecipe as guard

    names = set(dir(guard))
    # Assert — guard entry points + login gates still exactly in place
    assert {"editor_page", "api_dispatch_with_context", "urlpatterns"} <= names
    assert hasattr(guard, "_reject_out_of_jail_paths")
    assert hasattr(guard, "_reject_compose_write")


def test_unmapped_login_fails_closed_never_proxied(monkeypatch):
    # Arrange — blocker 4: mallory has no mapped uid. The old code caught
    # the SpawnerUnavailable and proxied her to the shared URL (another
    # uid's box); now she must fail closed BEFORE any transport happens
    monkeypatch.setenv(proxy.URL_ENV, "http://127.0.0.1:18096")
    monkeypatch.setenv(proxy.KEY_ENV, "k")
    monkeypatch.delenv(proxy.ALLOW_SHARED_ENV, raising=False)
    monkeypatch.setenv("FIGRECIPE_UID_MAP", "alice:10001")
    called = {"conn": False}

    class _MustNotRun:
        def __init__(self, *a, **k):
            called["conn"] = True
            raise AssertionError("transport must not run for unmapped logins")

    monkeypatch.setattr(proxy.http.client, "HTTPConnection", _MustNotRun)
    monkeypatch.setattr(proxy, "mint_token_for", lambda request: "T")
    # Act / Assert — fail closed at routing, no bytes proxied anywhere
    with pytest.raises(proxy.ContainerUnavailable):
        proxy._target_for(_authed_request(user="mallory"))
    with pytest.raises(proxy.ContainerUnavailable):
        proxy.proxy_request(_authed_request(user="mallory"), "")
    assert called["conn"] is False


def test_shared_fallback_is_dev_opt_in_only(monkeypatch):
    # Arrange — the shared URL survives only behind the explicit flag
    monkeypatch.setenv(proxy.URL_ENV, "http://127.0.0.1:18096")
    monkeypatch.setenv(proxy.KEY_ENV, "k")
    monkeypatch.setenv("FIGRECIPE_UID_MAP", "alice:10001")
    # Act — without the flag: fail closed
    monkeypatch.delenv(proxy.ALLOW_SHARED_ENV, raising=False)
    with pytest.raises(proxy.ContainerUnavailable):
        proxy._target_for(_authed_request(user="mallory"))
    # ... with the flag: dev single-container routing (loopback)
    monkeypatch.setenv(proxy.ALLOW_SHARED_ENV, "1")
    scheme, host, port = proxy._target_for(_authed_request(user="mallory"))
    assert (scheme, host, port) == ("http", "127.0.0.1", 18096)


def test_shared_fallback_refuses_non_loopback(monkeypatch):
    # Arrange — m8: even the dev fallback must not turn the hub into an
    # SSRF client via a misconfigured env URL
    monkeypatch.setenv(proxy.URL_ENV, "http://10.0.0.9:18096")
    monkeypatch.setenv(proxy.KEY_ENV, "k")
    monkeypatch.setenv(proxy.ALLOW_SHARED_ENV, "1")
    monkeypatch.setenv("FIGRECIPE_UID_MAP", "alice:10001")
    # Act / Assert
    with pytest.raises(proxy.ContainerUnavailable):
        proxy._target_for(_authed_request(user="mallory"))


def test_garbage_timeout_fails_closed(monkeypatch):
    # Arrange — m1: bare int() on TIMEOUT_ENV used to 500 on garbage
    monkeypatch.setenv(proxy.URL_ENV, "http://127.0.0.1:18096")
    monkeypatch.setenv(proxy.KEY_ENV, "k")
    monkeypatch.setenv(proxy.ALLOW_SHARED_ENV, "1")
    # Act / Assert — garbage, zero, and absurd values all fail closed
    for bad in ("not-a-number", "0", "-5", "99999"):
        monkeypatch.setenv(proxy.TIMEOUT_ENV, bad)
        with pytest.raises(proxy.ContainerUnavailable):
            proxy.proxy_request(_authed_request(), "", token="T")


def test_oversize_body_fails_closed(monkeypatch):
    # Arrange — m2: the hub worker must not buffer unbounded container bytes
    monkeypatch.setenv(proxy.URL_ENV, "http://127.0.0.1:18096")
    monkeypatch.setenv(proxy.KEY_ENV, "k")
    monkeypatch.setenv(proxy.ALLOW_SHARED_ENV, "1")
    monkeypatch.setenv(proxy.MAX_BODY_ENV, "16")

    class _Resp:
        status = 200

        def getheader(self, name, default=None):
            return "text/html"

        def read(self, *a):
            return b"x" * 17

    class _Conn:
        def __init__(self, *a, **k):
            pass

        def request(self, *a, **k):
            pass

        def getresponse(self):
            return _Resp()

        def close(self):
            pass

    monkeypatch.setattr(proxy.http.client, "HTTPConnection", _Conn)
    # Act / Assert — over-cap bodies raise (caller falls back in-process),
    # never a truncated 200
    with pytest.raises(proxy.ContainerUnavailable):
        proxy.proxy_request(_authed_request(), "", token="T")


@pytest.mark.parametrize(
    "evil_host",
    ["169.254.169.254", "evil.example.com", "10.0.0.9", "0.0.0.0"],
)
def test_proxy_refuses_non_loopback_host(monkeypatch, evil_host):
    # Arrange — SSRF gate (CodeQL py/partial-ssrf): even if routing is
    # compromised to point at a non-loopback host, no socket may open
    monkeypatch.setenv(proxy.URL_ENV, "http://127.0.0.1:18096")
    monkeypatch.setenv(proxy.KEY_ENV, "k")
    monkeypatch.setenv("FIGRECIPE_UID_MAP", "alice:10001")
    from apps.workspace.figrecipe_app.services import container_spawner as spawner

    own_port = spawner.user_port(10001)
    monkeypatch.setattr(
        spawner, "container_host_port", lambda request: (evil_host, own_port)
    )
    opened = {"conn": False}

    class _MustNotOpen:
        def __init__(self, *a, **k):
            opened["conn"] = True
            raise AssertionError("transport must not open for non-loopback hosts")

    monkeypatch.setattr(proxy.http.client, "HTTPConnection", _MustNotOpen)
    monkeypatch.setattr(proxy.http.client, "HTTPSConnection", _MustNotOpen)
    # Act / Assert — refused at routing AND pre-socket, never proxied
    with pytest.raises(proxy.ContainerUnavailable):
        proxy._target_for(_authed_request(user="alice"))
    with pytest.raises(proxy.ContainerUnavailable):
        proxy.proxy_request(_authed_request(user="alice"), "", token="T")
    assert opened["conn"] is False


def test_proxy_refuses_foreign_port(monkeypatch):
    # Arrange — mapped login whose routing disagrees with the per-uid
    # registry (another port on loopback): refused before any socket opens
    monkeypatch.setenv(proxy.URL_ENV, "http://127.0.0.1:18096")
    monkeypatch.setenv(proxy.KEY_ENV, "k")
    monkeypatch.setenv("FIGRECIPE_UID_MAP", "alice:10001")
    from apps.workspace.figrecipe_app.services import container_spawner as spawner

    own_port = spawner.user_port(10001)
    foreign_port = own_port + 1 if own_port < 65535 else own_port - 1
    assert foreign_port != own_port
    monkeypatch.setattr(
        spawner, "container_host_port", lambda request: ("127.0.0.1", foreign_port)
    )
    opened = {"conn": False}

    class _MustNotOpen:
        def __init__(self, *a, **k):
            opened["conn"] = True
            raise AssertionError("transport must not open for foreign ports")

    monkeypatch.setattr(proxy.http.client, "HTTPConnection", _MustNotOpen)
    monkeypatch.setattr(proxy.http.client, "HTTPSConnection", _MustNotOpen)
    # Act / Assert
    with pytest.raises(proxy.ContainerUnavailable):
        proxy.proxy_request(_authed_request(user="alice"), "", token="T")
    assert opened["conn"] is False
