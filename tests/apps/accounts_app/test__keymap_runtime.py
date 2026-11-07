"""Contract tests for the shell runtime keymap (server-resolved matchers)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from apps.infra.accounts_app.keymap_preferences import (
    InvalidKeymapPreference,
    bind_shortcut,
    empty_preferences,
    unbind_shortcut,
)
from apps.infra.accounts_app.keymap_runtime import (
    effective_keymap,
    parse_display_matcher,
    to_registry_sequence,
)
from apps.infra.accounts_app.views import settings_views


@pytest.mark.parametrize(
    ("sequence", "expected"),
    [
        ("Alt+A", {"key": "a", "ctrl": False, "alt": True, "shift": False, "meta": False}),
        ("Ctrl+U", {"key": "u", "ctrl": True, "alt": False, "shift": False, "meta": False}),
        (
            "Alt+Shift+T",
            {"key": "t", "ctrl": False, "alt": True, "shift": True, "meta": False},
        ),
        (
            "Alt+Shift+Left",
            {"key": "ArrowLeft", "ctrl": False, "alt": True, "shift": True, "meta": False},
        ),
        (
            "Alt+Right",
            {"key": "ArrowRight", "ctrl": False, "alt": True, "shift": False, "meta": False},
        ),
        ("ctrl + shift + F5", {"key": "F5", "ctrl": True, "alt": False, "shift": True, "meta": False}),
    ],
)
def test_parse_display_matcher_resolves_event_fields(sequence, expected):
    # Arrange / Act
    matcher = parse_display_matcher(sequence)
    # Assert
    assert matcher == expected


@pytest.mark.parametrize(
    "sequence",
    ["", "   ", "C-x C-s", "Alt++A", "Hyper+A", "Alt+NoSuchKey", "Alt+Shift"],
)
def test_parse_display_matcher_rejects_unsupported_sequences(sequence):
    # Arrange / Act / Assert
    with pytest.raises(InvalidKeymapPreference):
        parse_display_matcher(sequence)


@pytest.mark.parametrize(
    ("sequence", "expected"),
    [
        ("Alt+A", "M-A"),
        ("Ctrl+U", "C-U"),
        ("Alt+T", "M-T"),
        ("Alt+Shift+T", "M-S-T"),
        ("Alt+Left", "M-LFT"),
        ("Alt+Shift+Right", "M-S-RGT"),
    ],
)
def test_to_registry_sequence_bridges_to_the_ts_chord_grammar(sequence, expected):
    # Arrange / Act / Assert
    assert to_registry_sequence(sequence) == expected


def test_effective_keymap_serves_defaults_with_shell_matchers():
    # Arrange
    from scitex_ui.keymap import keymap_defaults

    # Act
    commands = effective_keymap(empty_preferences())
    # Assert
    assert set(commands) == set(keymap_defaults())
    upload = commands["file:upload"]
    assert upload["bound"] is True
    assert upload["sequence"] == "Ctrl+U"
    assert upload["match"] == {
        "key": "u",
        "ctrl": True,
        "alt": False,
        "shift": False,
        "meta": False,
    }
    assert upload["registry_sequence"] == "C-U"
    assert upload["scope"] == "global"


def test_hub_command_ids_mirror_the_published_catalog():
    # Arrange
    from scitex_ui.keymap import keymap_defaults

    # Act / Assert — the shell table must drift loudly, not silently.
    assert set(keymap_defaults()) == {
        "ai-panel:toggle",
        "file:upload",
        "pane:collapse-left",
        "pane:collapse-right",
        "pane:cycle-next",
        "pane:cycle-prev",
        "pane:focus-next",
        "pane:focus-prev",
    }
    assert set(effective_keymap(empty_preferences())) == set(keymap_defaults())


def test_effective_keymap_applies_a_user_override():
    # Arrange
    preferences = bind_shortcut(
        empty_preferences(), "global", "ai-panel:toggle", "Ctrl+Shift+A"
    )
    # Act
    commands = effective_keymap(preferences)
    # Assert
    toggle = commands["ai-panel:toggle"]
    assert (toggle["sequence"], toggle["match"], toggle["is_overridden"]) == (
        "Ctrl+Shift+A",
        {"key": "a", "ctrl": True, "alt": False, "shift": True, "meta": False},
        True,
    )


def test_effective_keymap_marks_unbound_commands_not_bound():
    # Arrange
    preferences = unbind_shortcut(empty_preferences(), "global", "file:upload")
    # Act
    commands = effective_keymap(preferences)
    # Assert
    assert commands["file:upload"] == {
        "scope": "global",
        "label": commands["file:upload"]["label"],
        "group": "Global",
        "default_sequence": "Ctrl+U",
        "sequence": None,
        "match": None,
        "registry_sequence": None,
        "bound": False,
        "is_overridden": False,
        "is_unbound": True,
    }


def test_effective_keymap_serves_page_mode_scopes_with_their_scope_attached():
    # Arrange
    defaults = {
        "scholar:search": {
            "label": "Search papers",
            "group": "Scholar",
            "scope": "scholar",
            "sequence": "Ctrl+K",
        }
    }
    preferences = bind_shortcut(
        empty_preferences(), "scholar", "scholar:search", "Ctrl+Shift+K"
    )
    # Act
    commands = effective_keymap(preferences, defaults=defaults)
    # Assert
    assert commands["scholar:search"]["scope"] == "scholar"
    assert commands["scholar:search"]["sequence"] == "Ctrl+Shift+K"
    assert commands["scholar:search"]["match"]["key"] == "k"


def _anonymous_request():
    return SimpleNamespace(method="GET", user=SimpleNamespace(is_authenticated=False))


def test_keymap_api_serves_defaults_to_anonymous_visitors():
    # Arrange
    request = _anonymous_request()
    # Act
    response = settings_views.keymap_api(request)
    # Assert
    payload = json.loads(response.content)
    assert payload["commands"]["file:upload"]["sequence"] == "Ctrl+U"
    assert payload["commands"]["file:upload"]["bound"] is True


def test_keymap_api_merges_an_authenticated_user_profile_without_creating_one():
    # Arrange
    created = []
    preferences = bind_shortcut(
        empty_preferences(), "global", "file:upload", "Ctrl+Shift+U"
    )
    profile = SimpleNamespace(keymap_preferences=preferences)
    request = SimpleNamespace(
        method="GET", user=SimpleNamespace(is_authenticated=True, profile=profile)
    )
    # Act
    response = settings_views.keymap_api(request)
    # Assert
    payload = json.loads(response.content)
    assert payload["commands"]["file:upload"]["sequence"] == "Ctrl+Shift+U"
    assert created == []


def test_keymap_api_without_a_profile_row_serves_defaults():
    # Arrange
    user = SimpleNamespace(is_authenticated=True, profile=None)
    request = SimpleNamespace(method="GET", user=user)
    # Act
    response = settings_views.keymap_api(request)
    # Assert
    payload = json.loads(response.content)
    assert payload["commands"]["ai-panel:toggle"]["sequence"] == "Alt+A"


def test_keymap_api_rejects_non_get_methods():
    # Arrange
    request = _anonymous_request()
    request.method = "POST"
    request.path = "/accounts/api/keymap/"
    # Act
    response = settings_views.keymap_api(request)
    # Assert
    assert response.status_code == 405


def test_keymap_api_has_a_stable_route():
    # Arrange / Act
    from django.urls import reverse

    # Assert
    assert reverse("accounts_app:keymap_api") == "/accounts/api/keymap/"
