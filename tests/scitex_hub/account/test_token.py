#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/account/test_token.py
"""Unit tests for ``scitex_hub.account.token`` Python parity.

Mirrors the hand-rolled fake-server pattern from
``tests/scitex_hub/test_project_create_category.py``: no mocks, no
``monkeypatch`` — production code exposes a ``request_fn`` /
transport-injection seam and tests pass a tiny ``_FakePost`` recording
the calls. Env vars are handled by ``yield``-based fixtures in
``conftest.py``.

One assertion per test (STX-TQ007); AAA marker comments mandatory
(STX-TQ002).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class _FakePost:
    """Hand-rolled stand-in for ``token._default_post``.

    Returns a configurable response dict and records the (url, body)
    of every call on ``self.calls`` for inspection.
    """

    response: dict[str, Any] = field(
        default_factory=lambda: {
            "status_code": 201,
            "json": {
                "token": "scitex_abcd1234efgh5678",
                "prefix": "scitex_abcd",
                "scopes": ["publish"],
                "name": "ci",
            },
            "text": "",
        }
    )
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def __call__(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((url, body))
        return self.response

    @property
    def last_body(self) -> dict[str, Any]:
        return self.calls[-1][1]

    @property
    def last_url(self) -> str:
        return self.calls[-1][0]


def test_account_namespace_exposes_token_submodule():
    # Arrange
    import scitex_hub

    # Act
    obj = scitex_hub.account.token

    # Assert
    assert obj is not None


def test_account_namespace_exposes_whoami_submodule():
    # Arrange
    import scitex_hub

    # Act
    obj = scitex_hub.account.whoami

    # Assert
    assert obj is not None


def test_token_create_requires_user_argument():
    # Arrange
    from scitex_hub.account import token

    raised: Exception | None = None

    # Act
    try:
        token.create(
            name="x",
            scopes=["publish"],
            password="pw",  # pragma: allowlist secret  # pragma: allowlist secret
        )
    except ValueError as exc:
        raised = exc

    # Assert
    assert raised is not None and "user=" in str(raised)


def test_token_create_requires_password_argument():
    # Arrange
    from scitex_hub.account import token

    raised: Exception | None = None

    # Act
    try:
        token.create(name="x", scopes=["publish"], user="u")
    except ValueError as exc:
        raised = exc

    # Assert
    assert raised is not None and "password=" in str(raised)


def test_token_create_posts_to_me_token_endpoint():
    # Arrange
    from scitex_hub.account import token

    fake = _FakePost()

    # Act
    token.create(
        name="ci",
        scopes=["publish"],
        user="ywatanabe",
        password="pw",  # pragma: allowlist secret
        server="https://hub.test.example",
        request_fn=fake,
    )

    # Assert
    assert fake.last_url == "https://hub.test.example/api/me/token/"


def test_token_create_sends_username_in_body():
    # Arrange
    from scitex_hub.account import token

    fake = _FakePost()

    # Act
    token.create(
        user="ywatanabe",
        password="pw",  # pragma: allowlist secret
        server="https://hub.test.example",
        request_fn=fake,
    )

    # Assert
    assert fake.last_body["username"] == "ywatanabe"


def test_token_create_sends_password_in_body():
    # Arrange
    from scitex_hub.account import token

    fake = _FakePost()

    # Act
    token.create(
        user="ywatanabe",
        password="pw",  # pragma: allowlist secret
        server="https://hub.test.example",
        request_fn=fake,
    )

    # Assert
    assert fake.last_body["password"] == "pw"  # pragma: allowlist secret


def test_token_create_default_scopes_are_publish():
    # Arrange
    from scitex_hub.account import token

    fake = _FakePost()

    # Act
    token.create(
        user="u",
        password="p",
        server="https://hub.test.example",
        request_fn=fake,
    )

    # Assert
    assert fake.last_body["scopes"] == ["publish"]


def test_token_create_explicit_scopes_round_trip():
    # Arrange
    from scitex_hub.account import token

    fake = _FakePost()

    # Act
    token.create(
        user="u",
        password="p",
        scopes=["publish", "future-scope"],
        server="https://hub.test.example",
        request_fn=fake,
    )

    # Assert
    assert fake.last_body["scopes"] == ["publish", "future-scope"]


def test_token_create_returns_minted_token_value():
    # Arrange
    from scitex_hub.account import token

    fake = _FakePost()

    # Act
    out = token.create(
        user="u",
        password="p",
        server="https://hub.test.example",
        request_fn=fake,
    )

    # Assert
    assert out["token"] == "scitex_abcd1234efgh5678"


def test_token_create_returns_prefix_field():
    # Arrange
    from scitex_hub.account import token

    fake = _FakePost()

    # Act
    out = token.create(
        user="u",
        password="p",
        server="https://hub.test.example",
        request_fn=fake,
    )

    # Assert
    assert out["prefix"] == "scitex_abcd"


def test_token_create_401_raises_runtime_error():
    # Arrange
    from scitex_hub.account import token

    fake = _FakePost(response={"status_code": 401, "json": {}, "text": "unauthorized"})
    raised: Exception | None = None

    # Act
    try:
        token.create(
            user="u",
            password="bad",  # pragma: allowlist secret
            server="https://hub.test.example",
            request_fn=fake,
        )
    except RuntimeError as exc:
        raised = exc

    # Assert
    assert raised is not None and "Authentication failed" in str(raised)


def test_token_create_429_raises_rate_limit_runtime_error():
    # Arrange
    from scitex_hub.account import token

    fake = _FakePost(response={"status_code": 429, "json": {}, "text": "rate limited"})
    raised: Exception | None = None

    # Act
    try:
        token.create(
            user="u",
            password="p",
            server="https://hub.test.example",
            request_fn=fake,
        )
    except RuntimeError as exc:
        raised = exc

    # Assert
    assert raised is not None and "rate-limited" in str(raised)


def test_token_create_400_surfaces_server_error_field():
    # Arrange
    from scitex_hub.account import token

    fake = _FakePost(
        response={
            "status_code": 400,
            "json": {"error": "scope not allowlisted"},
            "text": '{"error": "scope not allowlisted"}',
        }
    )
    raised: Exception | None = None

    # Act
    try:
        token.create(
            user="u",
            password="p",
            scopes=["root"],
            server="https://hub.test.example",
            request_fn=fake,
        )
    except RuntimeError as exc:
        raised = exc

    # Assert
    assert raised is not None and "scope not allowlisted" in str(raised)


def test_token_list_alias_points_at_list_underscore():
    # Arrange
    from scitex_hub.account import token

    # Act
    same = token.list is token.list_

    # Assert
    assert same


def test_default_scopes_constant_is_publish_only():
    # Arrange
    from scitex_hub.account.token import DEFAULT_SCOPES

    # Act
    actual = tuple(DEFAULT_SCOPES)

    # Assert
    assert actual == ("publish",)


# EOF
