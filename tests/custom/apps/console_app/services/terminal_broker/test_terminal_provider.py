#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/console_app/services/terminal_provider.py

Covers the Option A model-agnostic terminal sessions surface:
registry validation (unknown provider rejected), env-injection
composition (correct vars, key sourced server-side, absent for
anthropic-oauth), readonly-visitor gating, and no-key fail-loud.

No mocks (STX-NM001): collaborators are injected — the key lookup is a
hand-rolled fake callable, PTY chdir runs against a real tmp_path, and
broker handlers get a bare object because rejection happens before any
broker state is touched.
"""

import os
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.workspace.console_app.services.terminal_broker.session import BasePTY
from apps.workspace.console_app.services.terminal_provider import (
    AI_PROVIDER_SETTINGS_URL,
    DEFAULT_PROVIDER,
    TERMINAL_PROVIDERS,
    ProviderKeyMissingError,
    ProviderNotAllowedError,
    UnknownProviderError,
    list_terminal_providers,
    normalize_provider,
    resolve_provider_env,
    resolve_spawn_provider,
    validate_provider_request,
)


class FakeKeyLookup:
    """Hand-rolled key-store fake: records calls, returns a fixed key."""

    def __init__(self, key: str = ""):
        self.key = key
        self.calls: list[tuple[str, str]] = []

    def __call__(self, username: str, key_service: str) -> str:
        self.calls.append((username, key_service))
        return self.key


def _user(username="alice", pk=1, authenticated=True):
    return SimpleNamespace(username=username, pk=pk, is_authenticated=authenticated)


@pytest.fixture
def preserved_cwd():
    """BasePTY._prepare_child_env chdirs for real — restore after."""
    cwd = os.getcwd()
    yield
    os.chdir(cwd)


# ---------------------------------------------------------------------------
# Registry validation
# ---------------------------------------------------------------------------


class TestRegistryValidation:
    def test_registry_contains_exactly_approved_providers(self):
        # Arrange
        approved = {"anthropic-oauth", "anthropic-api-key", "deepseek", "mimo"}
        # Act
        registered = set(TERMINAL_PROVIDERS)
        # Assert
        assert registered == approved

    def test_default_provider_is_anthropic_oauth(self):
        # Arrange — module constant under test
        expected = "anthropic-oauth"
        # Act
        actual = DEFAULT_PROVIDER
        # Assert
        assert actual == expected

    def test_normalize_empty_string_returns_default(self):
        # Arrange
        raw = ""
        # Act
        normalized = normalize_provider(raw)
        # Assert
        assert normalized == DEFAULT_PROVIDER

    def test_normalize_none_returns_default(self):
        # Arrange
        raw = None
        # Act
        normalized = normalize_provider(raw)
        # Assert
        assert normalized == DEFAULT_PROVIDER

    def test_normalize_unknown_provider_raises_unknown_provider_error(self):
        # Arrange
        raw = "not-a-provider"
        # Act
        act = partial(normalize_provider, raw)
        # Assert
        with pytest.raises(UnknownProviderError):
            act()

    def test_unknown_provider_error_message_names_valid_providers(self):
        # Arrange
        raw = "not-a-provider"
        # Act
        try:
            normalize_provider(raw)
            message = ""
        except UnknownProviderError as exc:
            message = str(exc)
        # Assert
        assert all(pid in message for pid in list_terminal_providers())

    def test_normalize_free_form_url_rejected_as_provider_id(self):
        # Arrange — a client may NOT smuggle a base_url as an id
        raw = "https://evil.example.com/anthropic"
        # Act
        act = partial(normalize_provider, raw)
        # Assert
        with pytest.raises(UnknownProviderError):
            act()


# ---------------------------------------------------------------------------
# Env composition (key injected via hand-rolled lookup — server-side)
# ---------------------------------------------------------------------------


class TestEnvComposition:
    def test_oauth_provider_composes_empty_env(self):
        # Arrange
        lookup = FakeKeyLookup(key="sk-should-never-be-read")
        # Act
        env = resolve_provider_env("anthropic-oauth", "alice", key_lookup=lookup)
        # Assert
        assert env == {}

    def test_oauth_provider_never_consults_key_store(self):
        # Arrange
        lookup = FakeKeyLookup(key="sk-should-never-be-read")
        # Act
        resolve_provider_env("anthropic-oauth", "alice", key_lookup=lookup)
        # Assert
        assert lookup.calls == []

    def test_deepseek_env_sets_registry_base_url(self):
        # Arrange
        lookup = FakeKeyLookup(key="sk-test-key")
        # Act
        env = resolve_provider_env("deepseek", "alice", key_lookup=lookup)
        # Assert
        assert env["ANTHROPIC_BASE_URL"] == "https://api.deepseek.com/anthropic"

    def test_deepseek_env_sets_api_key_from_lookup(self):
        # Arrange
        lookup = FakeKeyLookup(key="sk-test-key")
        # Act
        env = resolve_provider_env("deepseek", "alice", key_lookup=lookup)
        # Assert
        assert env["ANTHROPIC_API_KEY"] == "sk-test-key"

    def test_deepseek_env_sets_model_and_small_fast_model(self):
        # Arrange
        lookup = FakeKeyLookup(key="sk-test-key")
        # Act
        env = resolve_provider_env("deepseek", "alice", key_lookup=lookup)
        # Assert
        assert (
            env["ANTHROPIC_MODEL"],
            env["ANTHROPIC_SMALL_FAST_MODEL"],
        ) == ("deepseek-chat", "deepseek-chat")

    def test_deepseek_env_sets_clean_per_provider_claude_config_dir(self):
        # Arrange
        lookup = FakeKeyLookup(key="sk-test-key")
        # Act
        env = resolve_provider_env("deepseek", "alice", key_lookup=lookup)
        # Assert
        assert env["CLAUDE_CONFIG_DIR"] == (
            "/home/alice/.scitex/claude-provider/deepseek"
        )

    def test_key_lookup_receives_username_and_key_service(self):
        # Arrange
        lookup = FakeKeyLookup(key="sk-test-key")
        # Act
        resolve_provider_env("deepseek", "alice", key_lookup=lookup)
        # Assert
        assert lookup.calls == [("alice", "deepseek")]

    def test_anthropic_api_key_env_omits_base_url_override(self):
        # Arrange
        lookup = FakeKeyLookup(key="sk-ant-key")
        # Act
        env = resolve_provider_env("anthropic-api-key", "bob", key_lookup=lookup)
        # Assert
        assert "ANTHROPIC_BASE_URL" not in env

    def test_anthropic_api_key_env_reads_anthropic_key_service(self):
        # Arrange
        lookup = FakeKeyLookup(key="sk-ant-key")
        # Act
        resolve_provider_env("anthropic-api-key", "bob", key_lookup=lookup)
        # Assert
        assert lookup.calls == [("bob", "anthropic")]

    def test_mimo_env_sets_xiaomi_gateway_base_url(self):
        # Arrange
        lookup = FakeKeyLookup(key="sk-mimo")
        # Act
        env = resolve_provider_env("mimo", "alice", key_lookup=lookup)
        # Assert
        assert env["ANTHROPIC_BASE_URL"] == (
            "https://token-plan-sgp.xiaomimimo.com/anthropic"
        )

    def test_mimo_env_omits_model_override_for_gateway_default(self):
        # Arrange
        lookup = FakeKeyLookup(key="sk-mimo")
        # Act
        env = resolve_provider_env("mimo", "alice", key_lookup=lookup)
        # Assert
        assert "ANTHROPIC_MODEL" not in env

    def test_missing_key_raises_provider_key_missing_error(self):
        # Arrange — key store has nothing for this user (fail-loud path)
        lookup = FakeKeyLookup(key="")
        # Act
        act = partial(resolve_provider_env, "deepseek", "alice", key_lookup=lookup)
        # Assert
        with pytest.raises(ProviderKeyMissingError):
            act()

    def test_missing_key_error_points_at_key_settings_page(self):
        # Arrange
        lookup = FakeKeyLookup(key="")
        # Act
        try:
            resolve_provider_env("deepseek", "alice", key_lookup=lookup)
            message = ""
        except ProviderKeyMissingError as exc:
            message = str(exc)
        # Assert
        assert AI_PROVIDER_SETTINGS_URL in message


# ---------------------------------------------------------------------------
# resolve_spawn_provider — key sourced server-side, client fields ignored
# ---------------------------------------------------------------------------

_INJECTION_MSG = {
    "username": "alice",
    "provider": "deepseek",
    # Injection attempts a client could send — all must be ignored
    "api_key": "sk-evil",
    "base_url": "https://evil.example.com",
    "env": {"ANTHROPIC_API_KEY": "sk-evil"},
}


class TestResolveSpawnProvider:
    def test_spawn_env_key_comes_from_server_side_lookup(self):
        # Arrange
        lookup = FakeKeyLookup(key="sk-from-store")
        # Act
        _, env = resolve_spawn_provider(dict(_INJECTION_MSG), key_lookup=lookup)
        # Assert
        assert env["ANTHROPIC_API_KEY"] == "sk-from-store"

    def test_spawn_env_base_url_comes_from_registry_not_client(self):
        # Arrange
        lookup = FakeKeyLookup(key="sk-from-store")
        # Act
        _, env = resolve_spawn_provider(dict(_INJECTION_MSG), key_lookup=lookup)
        # Assert
        assert env["ANTHROPIC_BASE_URL"] == "https://api.deepseek.com/anthropic"

    def test_spawn_msg_without_provider_field_uses_default(self):
        # Arrange
        lookup = FakeKeyLookup(key="sk-unused")
        # Act
        provider, _ = resolve_spawn_provider(
            {"username": "alice"}, key_lookup=lookup
        )
        # Assert
        assert provider == DEFAULT_PROVIDER

    def test_spawn_msg_with_unknown_provider_raises_error(self):
        # Arrange
        msg = {"username": "alice", "provider": "not-a-provider"}
        # Act
        act = partial(resolve_spawn_provider, msg, key_lookup=FakeKeyLookup())
        # Assert
        with pytest.raises(UnknownProviderError):
            act()


# ---------------------------------------------------------------------------
# Role / ownership gating (consumer-side)
# ---------------------------------------------------------------------------


class TestRoleGating:
    def test_gate_allows_default_provider_for_anonymous_session(self):
        # Arrange — no user object at all
        user = None
        # Act
        provider = validate_provider_request("", user, None)
        # Assert
        assert provider == DEFAULT_PROVIDER

    def test_gate_rejects_keyed_provider_for_anonymous_session(self):
        # Arrange
        anon = _user(username="", pk=None, authenticated=False)
        # Act
        act = partial(validate_provider_request, "deepseek", anon, _user("owner", 2))
        # Assert
        with pytest.raises(ProviderNotAllowedError):
            act()

    def test_gate_rejects_keyed_provider_for_readonly_visitor(self):
        # Arrange — the shared readonly account (VisitorPool constant)
        readonly = _user(username="readonly-visitor", pk=99)
        # Act
        act = partial(validate_provider_request, "deepseek", readonly, readonly)
        # Assert
        with pytest.raises(ProviderNotAllowedError):
            act()

    def test_gate_readonly_rejection_explains_read_only_state(self):
        # Arrange
        readonly = _user(username="readonly-visitor", pk=99)
        # Act
        try:
            validate_provider_request("deepseek", readonly, readonly)
            message = ""
        except ProviderNotAllowedError as exc:
            message = str(exc)
        # Assert
        assert "read-only" in message.lower()

    def test_gate_allows_default_provider_for_readonly_visitor(self):
        # Arrange
        readonly = _user(username="readonly-visitor", pk=99)
        # Act
        provider = validate_provider_request("anthropic-oauth", readonly, readonly)
        # Assert
        assert provider == DEFAULT_PROVIDER

    def test_gate_rejects_keyed_provider_for_non_owner_collaborator(self):
        # Arrange
        collaborator = _user("carol", pk=3)
        owner = _user("alice", pk=1)
        # Act
        act = partial(validate_provider_request, "deepseek", collaborator, owner)
        # Assert
        with pytest.raises(ProviderNotAllowedError):
            act()

    def test_gate_allows_keyed_provider_for_project_owner(self):
        # Arrange
        owner = _user("alice", pk=1)
        # Act
        provider = validate_provider_request("deepseek", owner, owner)
        # Assert
        assert provider == "deepseek"

    def test_gate_allows_keyed_provider_for_writable_visitor_slot(self):
        # Arrange — visitor-NNN slots use their OWN stored key
        visitor = _user("visitor-007", pk=7)
        # Act
        provider = validate_provider_request("deepseek", visitor, visitor)
        # Assert
        assert provider == "deepseek"

    def test_gate_rejects_unknown_provider_id_for_owner(self):
        # Arrange
        owner = _user("alice", pk=1)
        # Act
        act = partial(validate_provider_request, "gpt-o-mega", owner, owner)
        # Assert
        with pytest.raises(UnknownProviderError):
            act()


# ---------------------------------------------------------------------------
# PTY env application (broker-side, real chdir against tmp_path)
# ---------------------------------------------------------------------------


def _prepare_env(tmp_path: Path, provider_env=None) -> dict:
    pty = BasePTY(
        pty_id="t",
        username="alice",
        project_dir=tmp_path,
        provider_env=provider_env,
    )
    return pty._prepare_child_env()


class TestBasePTYProviderEnv:
    def test_prepare_child_env_applies_plain_provider_vars(
        self, tmp_path, preserved_cwd
    ):
        # Arrange
        provider_env = {"ANTHROPIC_API_KEY": "sk-x"}
        # Act
        env = _prepare_env(tmp_path, provider_env)
        # Assert
        assert env["ANTHROPIC_API_KEY"] == "sk-x"

    def test_prepare_child_env_mirrors_vars_with_apptainerenv_prefix(
        self, tmp_path, preserved_cwd
    ):
        # Arrange — --cleanenv exec path only honors APPTAINERENV_*
        provider_env = {"ANTHROPIC_API_KEY": "sk-x"}
        # Act
        env = _prepare_env(tmp_path, provider_env)
        # Assert
        assert env["APPTAINERENV_ANTHROPIC_API_KEY"] == "sk-x"

    def test_prepare_child_env_without_provider_adds_no_anthropic_vars(
        self, tmp_path, preserved_cwd
    ):
        # Arrange
        provider_env = None
        # Act
        env = _prepare_env(tmp_path, provider_env)
        # Assert
        assert not any("ANTHROPIC_API_KEY" == k for k in env)


# ---------------------------------------------------------------------------
# Broker handler wiring — unknown provider rejected before any PTY work
# ---------------------------------------------------------------------------


class TestHandlerRejectsUnknownProvider:
    def test_legacy_spawn_rejects_unknown_provider_with_error_status(self):
        # Arrange — bare objects: rejection happens before broker use
        from apps.workspace.console_app.services.terminal_broker._handlers_legacy import (
            handle_spawn_legacy,
        )

        broker, client = object(), object()
        msg = {"username": "alice", "provider": "not-a-provider"}
        # Act
        result = handle_spawn_legacy(broker, msg, client)
        # Assert
        assert result["status"] == "error"

    def test_shared_spawn_rejects_unknown_provider_with_error_status(self):
        # Arrange — bare objects: rejection happens before broker use
        from apps.workspace.console_app.services.terminal_broker._handlers_shared import (
            handle_spawn_shared,
        )

        broker, client = object(), object()
        msg = {
            "username": "alice",
            "project_slug": "proj",
            "provider": "not-a-provider",
        }
        # Act
        result = handle_spawn_shared(broker, msg, client)
        # Assert
        assert result["status"] == "error"

    def test_shared_spawn_error_names_the_bad_provider(self):
        # Arrange
        from apps.workspace.console_app.services.terminal_broker._handlers_shared import (
            handle_spawn_shared,
        )

        msg = {
            "username": "alice",
            "project_slug": "proj",
            "provider": "not-a-provider",
        }
        # Act
        result = handle_spawn_shared(object(), msg, object())
        # Assert
        assert "not-a-provider" in result["error"]


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__), "-v"])
