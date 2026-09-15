#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_dock_captions.py
"""Dock captions and sizing (operator, iPhone Home screenshot, 2026-09-14).

  * each dock app shows a short caption under its icon (Home / Projects /
    Chat / Apps), translated;
  * captions are 10-11px, app buttons keep a 44px tap target;
  * app icons match the Home tile icon at each width;
  * on a phone the grip and arrows move to a second row.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.utils import translation
from django.utils.translation import pgettext

from apps.infra.workspace_app.site_dock import DockItem

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _css(path: str) -> str:
    text = (_REPO_ROOT / path).read_text("utf-8")
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def _dock_css() -> str:
    return _css("static/shared/css/components/site-dock.css")


def _media_block(css: str, query: str) -> str:
    start = css.index(query)
    depth, i = 0, css.index("{", start)
    for j in range(i, len(css)):
        depth += {"{": 1, "}": -1}.get(css[j], 0)
        if depth == 0:
            return css[i : j + 1]
    return ""


@pytest.fixture(name="compiled_catalogs", scope="module")
def _compiled_catalogs():
    script = _REPO_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    subprocess.run([sys.executable, str(script)], cwd=_REPO_ROOT, check=True)
    translation.trans_real._translations.clear()
    yield
    translation.trans_real._translations.clear()


def test_my_projects_is_captioned_projects_in_the_dock():
    # Arrange
    item = DockItem(key="my_projects", label="My Projects", icon="", url="/apps/my-projects/")
    # Act
    caption = item.caption
    # Assert
    assert caption == "Projects"


def test_app_store_is_captioned_apps_in_the_dock():
    # Arrange
    item = DockItem(key="store", label="App Store", icon="", url="/apps/store/")
    # Act
    caption = item.caption
    # Assert
    assert caption == "Apps"


def test_other_apps_are_captioned_with_their_name():
    # Arrange
    item = DockItem(key="writer", label="Writer", icon="", url="/apps/writer/")
    # Act
    caption = item.caption
    # Assert
    assert caption == "Writer"


@pytest.mark.parametrize(
    ("caption", "expected"),
    [("Home", "ホーム"), ("Projects", "プロジェクト"), ("Chat", "チャット"), ("Apps", "アプリ")],
)
def test_dock_caption_is_translated_to_japanese(compiled_catalogs, caption, expected):
    # Arrange
    context = "app name"
    # Act
    with translation.override("ja"):
        rendered = pgettext(context, caption)
    # Assert
    assert rendered == expected


def test_caption_font_is_10_to_11px():
    # Arrange
    css = _dock_css()
    # Act
    size = float(re.search(r"--site-dock-label-size:\s*([0-9.]+)px", css).group(1))
    # Assert
    assert 10 <= size <= 11


def test_caption_stays_on_one_line_without_overflowing():
    # Arrange
    css = _dock_css()
    # Act
    rule = re.search(r"\.site-dock-app-label\s*\{([^}]*)\}", css).group(1)
    # Assert
    assert "white-space: nowrap" in rule and "text-overflow: ellipsis" in rule


def test_dock_app_button_keeps_a_44px_tap_target():
    # Arrange
    css = _dock_css()
    # Act
    rule = re.search(r"\.site-dock-apps \.site-dock-app\s*\{([^}]*)\}", css).group(1)
    # Assert
    assert re.search(r"min-width:\s*44px", rule)


def test_back_and_forward_are_44px_wide():
    # Arrange
    css = _dock_css()
    # Act
    rule = re.search(r"\.site-dock-history\s*\{([^}]*)\}", css).group(1)
    # Assert
    assert re.search(r"(?<![-\w])width:\s*44px", rule)


def test_phone_dock_icon_matches_the_phone_tile_icon():
    # Arrange
    tile = _media_block(
        _css("apps/workspace/apps_app/static/apps_app/css/launcher/mobile.css"),
        "@media (max-width: 640px)",
    )
    dock = _media_block(_dock_css(), "@media (min-width: 0px)")
    # Act
    sizes = (
        re.search(r"--launcher-icon-size:\s*(\d+)px", tile).group(1),
        re.search(r"--site-dock-icon:\s*(\d+)px", dock).group(1),
    )
    # Assert
    assert sizes[0] == sizes[1]


def test_desktop_uses_the_canonical_mobile_dock_icon_size():
    # Arrange
    dock = _media_block(_dock_css(), "@media (min-width: 0px)")
    # Act
    size = re.search(r"--site-dock-icon:\s*(\d+)px", dock).group(1)
    # Assert
    assert size == "60"


def test_phone_dock_gives_the_apps_their_own_row():
    # Arrange
    phone = _media_block(_dock_css(), "@media (min-width: 0px)")
    # Act
    rule = re.search(r"\.site-dock-apps\s*\{([^}]*)\}", phone).group(1)
    # Assert
    assert re.search(r"grid-column:\s*1\s*/\s*-1", rule)


def test_phone_second_row_is_back_grip_forward():
    # Operator 2026-09-14: [<] far left, wide grip in the centre, [>] far right.
    # Arrange
    phone = _media_block(_dock_css(), "@media (min-width: 0px)")
    # Act
    columns = tuple(
        re.search(selector + r"\s*\{[^}]*?grid-column:\s*(\d+)", phone).group(1)
        for selector in (
            r"\.site-dock-history",
            r"\.site-dock-grabber",
            r"\.site-dock-history\[data-dock-forward\]",
        )
    )
    # Assert
    assert columns == ("1", "2", "3")


def test_phone_grip_fills_the_centre_between_44px_arrows():
    # Arrange
    phone = _media_block(_dock_css(), "@media (min-width: 0px)")
    # Act
    rule = re.search(r"\.site-dock\s*\{([^}]*)\}", phone).group(1)
    # Assert
    assert re.search(r"grid-template-columns:\s*44px\s+minmax\(0,\s*1fr\)\s+44px", rule)
