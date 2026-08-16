#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Log-redaction tests for the terminal model-provider spawn path.

Asserts the CodeQL-hardened invariant: the user's decrypted API key must
NEVER appear in captured log output while the spawn path composes the
provider env (``resolve_spawn_provider`` is exactly what the broker
spawn handlers run; the key lookup is injected so the suite stays
DB-free like the rest of the terminal-broker tests).

No mocks (STX-NM001): the lookup is a plain callable returning a fixed
secret; log capture uses pytest's caplog across ALL loggers at DEBUG.
"""

import logging
import os

import pytest

from apps.workspace.console_app.services.terminal_provider import (
    resolve_provider_env,
    resolve_spawn_provider,
)

_SECRET = "sk-test-terminal-secret-0123456789"  # pragma: allowlist secret


def _fake_lookup(_username: str, _key_service: str) -> str:
    return _SECRET


class TestSpawnPathLogRedaction:
    def test_spawn_resolution_env_receives_key_from_lookup(self, caplog):
        # Arrange — the exact resolution the broker spawn handlers run
        caplog.set_level(logging.DEBUG)
        msg = {"username": "alice", "provider": "deepseek"}
        # Act
        _, env = resolve_spawn_provider(msg, key_lookup=_fake_lookup)
        # Assert — the key really flowed through (makes the companion
        # log assertion meaningful, not vacuous)
        assert env["ANTHROPIC_API_KEY"] == _SECRET

    def test_spawn_resolution_never_logs_key_value(self, caplog):
        # Arrange
        caplog.set_level(logging.DEBUG)
        msg = {"username": "alice", "provider": "deepseek"}
        # Act
        resolve_spawn_provider(msg, key_lookup=_fake_lookup)
        # Assert
        assert _SECRET not in caplog.text

    def test_env_composition_never_logs_key_value(self, caplog):
        # Arrange
        caplog.set_level(logging.DEBUG)
        # Act
        resolve_provider_env("deepseek", "alice", key_lookup=_fake_lookup)
        # Assert
        assert _SECRET not in caplog.text

    def test_composition_log_line_mentions_provider_only(self, caplog):
        # Arrange — the INFO line must identify the injection without
        # referencing the env dict (CodeQL clear-text-logging hardening)
        caplog.set_level(logging.INFO)
        # Act
        resolve_provider_env("deepseek", "alice", key_lookup=_fake_lookup)
        # Assert
        assert "provider=deepseek" in caplog.text


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__), "-v"])
