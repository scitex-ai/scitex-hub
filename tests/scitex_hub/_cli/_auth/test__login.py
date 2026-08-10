#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Behavioural test for ``scitex-hub auth login``'s HTTP helper.

Phase-1 PR-5 / card #2. Pins:

  - ``_post_mint`` posts ``{username, password, scopes, name}`` to
    ``/api/me/token/`` and returns the parsed JSON on 201.
  - On non-201, it raises ``requests.HTTPError`` carrying the response.

Per repo STX-NM rule: NO ``unittest.mock``. We use a hand-rolled fake
:class:`requests.Session` stand-in that records the call and returns a
canned :class:`requests.Response`. That matches the no-mocks pattern
used by ``tests/scitex_hub/test_account_cli_grammar.py``.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
import requests

from scitex_hub._cli._auth._login import _post_mint


class _FakeResponse:
    """Minimal :class:`requests.Response` stand-in (status + json + text)."""

    def __init__(self, status_code: int, payload: dict[str, Any] | None = None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = json.dumps(self._payload)

    def json(self) -> dict[str, Any]:
        return self._payload


class _RecordingSession:
    """Fake ``requests.Session`` capturing one ``.post()`` call."""

    def __init__(self, response: _FakeResponse):
        self._response = response
        self.last_url: str | None = None
        self.last_json: dict[str, Any] | None = None
        self.last_timeout: float | None = None

    def post(self, url: str, json: dict[str, Any], timeout: float) -> _FakeResponse:
        self.last_url = url
        self.last_json = json
        self.last_timeout = timeout
        return self._response


def test_post_mint_returns_json_on_201():
    # Arrange
    payload = {
        "token": "scitex_abcdef0123456789",
        "prefix": "scitex_a",
        "scopes": ["publish"],
    }
    session = _RecordingSession(_FakeResponse(201, payload))

    # Act
    actual = _post_mint(
        "https://hub.example.com",
        "alice",
        "PW_PLACEHOLDER",
        ("publish",),
        "test-token",
        session=session,
    )

    # Assert
    assert actual == payload


def test_post_mint_targets_me_token_endpoint():
    # Arrange
    session = _RecordingSession(_FakeResponse(201, {"token": "scitex_x"}))

    # Act
    _post_mint(
        "https://hub.example.com",
        "alice",
        "PW_PLACEHOLDER",
        ("publish",),
        "n",
        session=session,
    )

    # Assert
    assert session.last_url == "https://hub.example.com/api/me/token/"


def test_post_mint_body_includes_credentials_and_scopes():
    # Arrange
    session = _RecordingSession(_FakeResponse(201, {"token": "scitex_x"}))

    # Act
    _post_mint(
        "https://hub.example.com",
        "alice",
        "PW_PLACEHOLDER",
        ("publish",),
        "from-laptop",
        session=session,
    )

    # Assert
    assert session.last_json == {
        "username": "alice",
        "password": "PW_PLACEHOLDER",  # pragma: allowlist secret
        "scopes": ["publish"],
        "name": "from-laptop",
    }


def _raises_on_status(status: int) -> requests.HTTPError:
    """Shared helper: call ``_post_mint`` against a canned status."""
    session = _RecordingSession(_FakeResponse(status, {"error": "x"}))
    with pytest.raises(requests.HTTPError) as exc_info:
        _post_mint(
            "https://hub.example.com",
            "alice",
            "pw",
            ("publish",),
            "n",
            session=session,
        )
    return exc_info.value


def test_post_mint_raises_httperror_on_401():
    # Arrange
    session = _RecordingSession(_FakeResponse(401, {"error": "invalid_credentials"}))

    # Act
    def _call():
        _post_mint(
            "https://hub.example.com",
            "alice",
            "wrong",
            ("publish",),
            "n",
            session=session,
        )

    # Assert
    with pytest.raises(requests.HTTPError):
        _call()


def test_post_mint_on_401_attaches_response_with_status_401():
    # Arrange
    err = _raises_on_status(401)

    # Act
    actual = err.response.status_code

    # Assert
    assert actual == 401


def test_post_mint_raises_httperror_on_5xx():
    # Arrange
    session = _RecordingSession(_FakeResponse(503, {"error": "service_unavailable"}))

    # Act
    def _call():
        _post_mint(
            "https://hub.example.com",
            "alice",
            "PW_PLACEHOLDER",
            ("publish",),
            "n",
            session=session,
        )

    # Assert
    with pytest.raises(requests.HTTPError):
        _call()


def test_post_mint_on_5xx_attaches_response_with_status_503():
    # Arrange
    err = _raises_on_status(503)

    # Act
    actual = err.response.status_code

    # Assert
    assert actual == 503


def test_auth_group_registers_login_verb():
    # Arrange
    from scitex_hub._cli._auth import auth

    # Act
    actual = "login" in auth.commands

    # Assert
    assert actual is True


def test_main_cli_registers_auth_group():
    # Arrange — wire-through guard so a future refactor can't silently
    # drop the ``auth`` group from the top-level CLI tree.
    from scitex_hub._cli.main import main

    # Act
    actual = "auth" in main.commands

    # Assert
    assert actual is True


# ---------------------------------------------------------------------
# CLI spec §2 — the non-TTY refusal guard.
#
# These prove the guard that lets ``auth_login`` sit on the allowlist in
# tests/scitex_hub/_cli/test_interactive_prompt_call_sites.py. That scan
# only checks a prompt is DECLARED intentional; these check it actually
# cannot block an unattended caller. An allowlist whose entries are never
# proved is just a list of good intentions.
#
# CliRunner's stdin is not a terminal, so invoking with no credentials
# reproduces exactly the agent/pipeline case: before the fix this reached
# ``click.prompt`` and aborted on EOF naming nothing.
# ---------------------------------------------------------------------


def _invoke_login_without_credentials():
    """Run ``auth login`` with no flags on a non-TTY stdin."""
    from click.testing import CliRunner

    from scitex_hub._cli._auth._login import auth_login

    return CliRunner().invoke(auth_login, [], input="")


def test_login_without_tty_refuses_instead_of_prompting():
    """Exit 2 (usage error), not 1 (prompt aborted on EOF)."""
    # Arrange
    expected_exit_code = 2

    # Act
    result = _invoke_login_without_credentials()

    # Assert
    assert result.exit_code == expected_exit_code, (
        "`auth login` with no credentials and no terminal should refuse with "
        f"a usage error (exit 2), got exit {result.exit_code}. Exit 1 means it "
        "reached click.prompt and aborted on EOF — the §2 hang, merely dressed "
        f"as an error.\nOutput:\n{result.output}"
    )


def test_login_without_tty_never_emits_a_prompt():
    """No prompt text reaches the caller — the §2 property itself."""
    # Arrange
    prompt_text = "Username"

    # Act
    result = _invoke_login_without_credentials()

    # Assert
    assert prompt_text not in result.output, (
        "`auth login` emitted an interactive prompt with no terminal "
        "attached. An unanswered prompt is a hang for any agent or pipeline "
        f"driving this CLI.\nOutput:\n{result.output}"
    )


def test_login_without_tty_names_the_missing_flag():
    """The refusal is actionable: it names the flag to pass."""
    # Arrange
    expected_hint = "--user/-u"

    # Act
    result = _invoke_login_without_credentials()

    # Assert
    assert expected_hint in result.output, (
        "the refusal did not name the missing flag, so the caller is told "
        "what broke but not what to do. An error that only states the failure "
        f"is half-written.\nOutput:\n{result.output}"
    )


# EOF
