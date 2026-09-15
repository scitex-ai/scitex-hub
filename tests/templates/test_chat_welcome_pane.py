"""Full-page Chat welcome: no quick-action chips, navy logo in light mode, tall input."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PANE_PATH = REPO / "templates/global_base_partials/workspace_chat_pane.html"
CSS_PATH = REPO / "static/shared/css/components/workspace-chat.css"
TS_PATH = REPO / "static/shared/ts/components/chat-welcome.ts"


def test_quick_action_chips_are_gone():
    # Arrange
    path = PANE_PATH
    # Act
    pane = path.read_text(encoding="utf-8")
    # Assert
    assert "chat-shortcut-btn" not in pane


def test_welcome_uses_the_official_navy_circle_icon():
    # Arrange
    pattern = r"scitex-icon-navy-inverted\.svg[^>]*chat-welcome-logo"
    # Act
    pane = PANE_PATH.read_text(encoding="utf-8")
    # Assert
    assert re.search(pattern, pane, re.S)


def test_light_mode_halo_is_a_visible_navy_tint():
    # Arrange
    tokens = ("--chat-halo-rgb: 30, 41, 59;", "--chat-halo-glow: 0.18;")
    # Act
    css = CSS_PATH.read_text(encoding="utf-8")
    # Assert
    assert all(t in css for t in tokens)


def test_halo_keeps_the_original_4s_pulse():
    # Arrange
    rule = "animation: chat-logo-pulse 4s ease-in-out infinite"
    # Act
    css = CSS_PATH.read_text(encoding="utf-8")
    # Assert
    assert rule in css


def test_placeholder_lists_three_examples():
    # Arrange
    pattern = r'placeholder="([^"]*)"'
    # Act
    placeholder = re.search(pattern, PANE_PATH.read_text(encoding="utf-8")).group(1)
    # Assert
    assert placeholder.count("{{ bullet }}") == 3


def test_accent_is_the_official_scitex_navy():
    # Arrange
    token = "--chat-brand-navy: var(--color-primary, #1a2a40)"
    # Act
    css = CSS_PATH.read_text(encoding="utf-8")
    # Assert
    assert token in css


def test_input_is_five_lines_tall_on_phones():
    # Arrange
    rule = "min-height: 7.5em"
    # Act
    css = CSS_PATH.read_text(encoding="utf-8")
    # Assert
    assert rule in css


def test_input_auto_grows():
    # Arrange
    marker = "scrollHeight"
    # Act
    ts = TS_PATH.read_text(encoding="utf-8")
    # Assert
    assert marker in ts
