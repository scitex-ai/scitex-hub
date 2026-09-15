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


def test_light_mode_has_no_grey_halo_fill():
    # Arrange
    token = "--chat-halo-fill: 0;"
    # Act
    css = CSS_PATH.read_text(encoding="utf-8")
    # Assert
    assert token in css


def test_accent_is_the_official_scitex_navy():
    # Arrange
    token = "--chat-brand-navy: #1a2a40"
    # Act
    css = CSS_PATH.read_text(encoding="utf-8")
    # Assert
    assert token in css


def test_input_is_96px_tall_on_phones():
    # Arrange
    rule = "min-height: 96px"
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
