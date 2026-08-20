#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/account/test_whoami.py
"""Unit tests for ``scitex_hub.account.whoami``.

Same hand-rolled fake-transport pattern as ``test_token.py`` — no
``monkeypatch``, env vars handled via ``yield``-based fixtures in
``conftest.py`` (``env_token``, ``env_no_token_and_homeless``). One
assertion per test, AAA-marker comments mandatory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class _FakeGet:
    """Hand-rolled stand-in for ``whoami._default_get``."""

    response: dict[str, Any] = field(
        default_factory=lambda: {
            "status_code": 200,
            "json": {
                "username": "ywatanabe",
                "email": "ywatanabe@scitex.ai",
            },
            "text": "",
        }
    )
    calls: list[tuple[str, dict[str, str]]] = field(default_factory=list)

    def __call__(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        self.calls.append((url, headers))
        return self.response

    @property
    def last_url(self) -> str:
        return self.calls[-1][0]

    @property
    def last_headers(self) -> dict[str, str]:
        return self.calls[-1][1]


def test_whoami_unauthenticated_raises_runtime_error(env_no_token_and_homeless):
    # Arrange
    from scitex_hub.account import whoami as whoami_mod

    raised: Exception | None = None

    # Act
    try:
        whoami_mod.whoami()
    except RuntimeError as exc:
        raised = exc

    # Assert
    assert raised is not None and "not logged in" in str(raised)


def test_whoami_hits_me_endpoint(env_token):
    # Arrange
    from scitex_hub.account import whoami as whoami_mod

    fake = _FakeGet()

    # Act
    whoami_mod.whoami(server="https://hub.test.example", request_fn=fake)

    # Assert
    assert fake.last_url == "https://hub.test.example/api/me/"


def test_whoami_sends_bearer_header(env_token):
    # Arrange
    from scitex_hub.account import whoami as whoami_mod

    fake = _FakeGet()

    # Act
    whoami_mod.whoami(server="https://hub.test.example", request_fn=fake)

    # Assert
    assert fake.last_headers["Authorization"] == "Bearer scitex_test_token"


def test_whoami_returns_username(env_token):
    # Arrange
    from scitex_hub.account import whoami as whoami_mod

    fake = _FakeGet()

    # Act
    out = whoami_mod.whoami(server="https://hub.test.example", request_fn=fake)

    # Assert
    assert out["username"] == "ywatanabe"


def test_whoami_returns_email(env_token):
    # Arrange
    from scitex_hub.account import whoami as whoami_mod

    fake = _FakeGet()

    # Act
    out = whoami_mod.whoami(server="https://hub.test.example", request_fn=fake)

    # Assert
    assert out["email"] == "ywatanabe@scitex.ai"


def test_whoami_401_raises_token_expired(env_token):
    # Arrange
    from scitex_hub.account import whoami as whoami_mod

    fake = _FakeGet(response={"status_code": 401, "json": {}, "text": "unauthorized"})
    raised: Exception | None = None

    # Act
    try:
        whoami_mod.whoami(server="https://hub.test.example", request_fn=fake)
    except RuntimeError as exc:
        raised = exc

    # Assert
    assert raised is not None and "expired" in str(raised).lower()


def test_whoami_server_override_takes_precedence(env_token, env_url):
    # Arrange
    from scitex_hub.account import whoami as whoami_mod

    fake = _FakeGet()

    # Act
    whoami_mod.whoami(server="https://override.example", request_fn=fake)

    # Assert
    assert fake.last_url == "https://override.example/api/me/"


# EOF
