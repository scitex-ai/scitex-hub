#!/usr/bin/env python3
"""The mobile header menu: a labelled close control and translated entries.

2026-09-14 iPhone standalone-PWA report: the close "x" was hard to see and the
menu's labels ("Toggle dark mode", "Keyboard Shortcuts") stayed English under
Japanese. The layout half is verified by browser screenshots on the PR; this
file pins the markup half.

Every translation assertion is paired with its English control, because a
missing catalog entry renders the English msgid silently (see
tests/config/test_i18n_landing.py for the full argument).

No mocks. One assertion per test.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.utils import translation

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEADER_TEMPLATE = "global_base_partials/global_header.html"
MENU_MARKER = 'id="mobile-header-menu"'


@pytest.fixture(scope="module", autouse=True)
def compiled_catalogs():
    """Compile locale/**/*.po -> .mo so the render reads the real catalog."""
    script = PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    result = subprocess.run(
        [sys.executable, str(script)], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    translation.trans_real._translations.clear()
    yield


def _render_header(language: str) -> str:
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    context = {"request": request, "user": request.user, "SCITEX_FAVICON": "favicon.svg"}
    with translation.override(language):
        return render_to_string(HEADER_TEMPLATE, context)


def _menu(html: str) -> str:
    return html[html.index(MENU_MARKER):]


def _hamburger_tag(html: str) -> str:
    match = re.search(r'<button\b[^>]*id="mobile-hamburger-btn"[^>]*>', html)
    return match.group(0) if match else ""


def test_close_control_has_an_aria_label():
    # Arrange
    html = _render_header("en")
    # Act
    tag = _hamburger_tag(html)
    # Assert
    assert re.search(r'\baria-label="[^"]+"', tag)


def test_close_control_carries_the_close_label():
    """The inline handler swaps aria-label to this value while the menu is open."""
    # Arrange
    html = _render_header("en")
    # Act
    tag = _hamburger_tag(html)
    # Assert
    assert 'data-label-close="Close menu"' in tag


def test_close_control_names_the_menu_it_controls():
    # Arrange
    html = _render_header("en")
    # Act
    tag = _hamburger_tag(html)
    # Assert
    assert 'aria-controls="mobile-header-menu"' in tag


def test_close_control_starts_collapsed():
    # Arrange
    html = _render_header("en")
    # Act
    tag = _hamburger_tag(html)
    # Assert
    assert 'aria-expanded="false"' in tag


def test_ja_menu_translates_toggle_dark_mode():
    # Arrange
    expected = "ダークモードに切り替える"
    # Act
    menu = _menu(_render_header("ja"))
    # Assert
    assert expected in menu


def test_en_menu_keeps_toggle_dark_mode():
    """Control for the test above."""
    # Arrange
    expected = "Switch to dark mode"
    # Act
    menu = _menu(_render_header("en"))
    # Assert
    assert expected in menu


def test_ja_menu_translates_keyboard_shortcuts():
    # Arrange
    expected = "キーボードショートカット"
    # Act
    menu = _menu(_render_header("ja"))
    # Assert
    assert expected in menu


def test_ja_close_label_is_translated():
    # Arrange
    html = _render_header("ja")
    # Act
    tag = _hamburger_tag(html)
    # Assert
    assert 'data-label-close="メニューを閉じる"' in tag
