"""Contract tests for persisted per-user keymap overrides."""

from __future__ import annotations

import pytest

from apps.infra.accounts_app.keymap_preferences import (
    KeymapConflictError,
    bind_shortcut,
    build_shortcut_rows,
    empty_preferences,
    reset_shortcuts,
    unbind_shortcut,
)


def test_bind_creates_a_versioned_scope_override_without_mutating_input():
    # Arrange
    original = empty_preferences()
    # Act
    updated = bind_shortcut(original, "global", "ai-panel:toggle", "Alt+Shift+A")
    # Assert
    assert (updated["version"], updated["bindings"], original) == (
        1,
        {"global": {"ai-panel:toggle": "Alt+Shift+A"}},
        {"version": 1, "bindings": {}, "unbound": {}},
    )


def test_rebinding_a_command_replaces_its_sequence():
    # Arrange
    current = bind_shortcut(empty_preferences(), "global", "ai-panel:toggle", "Alt+A")
    # Act
    updated = bind_shortcut(current, "global", "ai-panel:toggle", "Alt+Shift+A")
    # Assert
    assert updated["bindings"]["global"]["ai-panel:toggle"] == "Alt+Shift+A"


def test_same_sequence_in_the_same_scope_reports_a_conflict():
    # Arrange
    current = bind_shortcut(empty_preferences(), "global", "ai-panel:toggle", "Alt+A")
    # Act / Assert
    with pytest.raises(KeymapConflictError, match="ai-panel:toggle"):
        bind_shortcut(current, "global", "pane:focus-next", " alt + a ")


def test_same_sequence_is_allowed_in_different_page_modes():
    # Arrange
    current = bind_shortcut(empty_preferences(), "writer", "writer:save", "Ctrl+S")
    # Act
    updated = bind_shortcut(current, "scholar", "scholar:save", "Ctrl+S")
    # Assert
    assert updated["bindings"]["scholar"] == {"scholar:save": "Ctrl+S"}


def test_unbind_removes_an_override_and_marks_the_command_disabled():
    # Arrange
    current = bind_shortcut(empty_preferences(), "global", "file:upload", "Ctrl+U")
    # Act
    updated = unbind_shortcut(current, "global", "file:upload")
    # Assert
    assert updated == {
        "version": 1,
        "bindings": {},
        "unbound": {"global": ["file:upload"]},
    }


def test_binding_a_disabled_command_enables_it_again():
    # Arrange
    current = unbind_shortcut(empty_preferences(), "global", "file:upload")
    # Act
    updated = bind_shortcut(current, "global", "file:upload", "Ctrl+Shift+U")
    # Assert
    assert updated == {
        "version": 1,
        "bindings": {"global": {"file:upload": "Ctrl+Shift+U"}},
        "unbound": {},
    }


def test_reset_one_command_removes_both_override_and_disabled_marker():
    # Arrange
    current = unbind_shortcut(
        bind_shortcut(empty_preferences(), "global", "file:upload", "Ctrl+Shift+U"),
        "global",
        "file:upload",
    )
    # Act
    updated = reset_shortcuts(current, scope="global", command_id="file:upload")
    # Assert
    assert updated == empty_preferences()


def test_reset_all_returns_empty_preferences():
    # Arrange
    current = bind_shortcut(empty_preferences(), "writer", "writer:save", "Ctrl+S")
    # Act
    updated = reset_shortcuts(current)
    # Assert
    assert updated == empty_preferences()


def test_user_profile_keymap_preferences_uses_a_callable_empty_default():
    # Arrange
    from apps.infra.accounts_app.models import UserProfile

    # Act
    field = UserProfile._meta.get_field("keymap_preferences")
    # Assert
    assert field.default() == empty_preferences()


def test_shortcut_rows_show_effective_override_and_default_sequence():
    # Arrange
    defaults = {
        "ai-panel:toggle": {
            "label": "Toggle AI panel",
            "group": "Global",
            "sequence": "Alt+A",
        }
    }
    preferences = bind_shortcut(
        empty_preferences(), "global", "ai-panel:toggle", "Alt+Shift+A"
    )
    # Act
    rows = build_shortcut_rows(defaults, preferences)
    # Assert
    assert rows[0] == {
        "command_id": "ai-panel:toggle",
        "label": "Toggle AI panel",
        "group": "Global",
        "scope": "global",
        "default_sequence": "Alt+A",
        "effective_sequence": "Alt+Shift+A",
        "is_overridden": True,
        "is_unbound": False,
    }


def test_shortcut_rows_searches_label_group_and_command_id_case_insensitively():
    # Arrange
    defaults = {
        "ai-panel:toggle": {
            "label": "Toggle AI panel",
            "group": "Global",
            "sequence": "Alt+A",
        },
        "file:upload": {
            "label": "Upload files",
            "group": "Files",
            "sequence": "Ctrl+U",
        },
    }
    # Act
    rows = build_shortcut_rows(defaults, empty_preferences(), query="UPLOAD")
    # Assert
    assert [row["command_id"] for row in rows] == ["file:upload"]
