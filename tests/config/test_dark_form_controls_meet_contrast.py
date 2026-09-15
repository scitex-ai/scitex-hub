"""Dark-theme form fields must reach WCAG AA (4.5:1) with the real tokens.

The dark ``.form-control`` / ``.form-select`` rules painted fields with
``--scitex-color-01-light``, a light-palette literal (#444) that the dark
palette never redefines, under ``--scitex-color-06`` text: 3.2:1, grey on grey
(the /new/ project-type picker on phones). These tests resolve each declared
pair through scitex-ui's shipped dark palette and compute the ratio, so a token
swap that looks harmless in review still fails here.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_INPUTS_CSS = _REPO_ROOT / "static" / "shared" / "css" / "components" / "forms" / "inputs.css"
_SELECT_CSS = _REPO_ROOT / "static" / "shared" / "css" / "components" / "select.css"
_DECL_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;]+);")
_VAR_RE = re.compile(r"^var\(\s*(--[\w-]+)\s*(?:,\s*([^)]+))?\)$")


def _palette_dir() -> Path:
    spec = importlib.util.find_spec("scitex_ui")
    if spec is None or not spec.origin:
        pytest.skip("scitex_ui is not installed")
    return Path(spec.origin).resolve().parent / "static" / "scitex_ui" / "css" / "primitives" / "colors"


def _dark_tokens() -> dict[str, str]:
    tokens: dict[str, str] = {}
    # Dark is imported after light and wins on equal specificity.
    for name in ("_light.css", "_dark.css"):
        text = re.sub(r"/\*.*?\*/", "", (_palette_dir() / name).read_text(), flags=re.S)
        tokens.update({k: v.strip() for k, v in _DECL_RE.findall(text)})
    return tokens


def _resolve(value: str, tokens: dict[str, str]) -> str:
    value = value.strip()
    for _ in range(10):
        match = _VAR_RE.match(value)
        if not match:
            return value
        value = tokens.get(match.group(1), match.group(2) or "").strip()
    return value


def _rule(css: Path, selector: str) -> dict[str, str]:
    text = re.sub(r"/\*.*?\*/", "", css.read_text(), flags=re.S)
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", text)
    return dict((k.strip(), v.strip()) for k, v in re.findall(r"([\w-]+)\s*:\s*([^;]+);", match.group(1)))


def _luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(fg: str, bg: str) -> float:
    high, low = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def test_dark_form_control_text_meets_aa():
    # Arrange
    tokens = _dark_tokens()
    rule = _rule(_INPUTS_CSS, '[data-theme="dark"] .form-control')
    # Act
    ratio = _contrast(_resolve(rule["color"], tokens), _resolve(rule["background-color"], tokens))
    # Assert
    assert ratio >= 4.5, f"dark .form-control text contrast {ratio:.2f}:1"


def test_dark_form_control_placeholder_meets_aa():
    # Arrange
    tokens = _dark_tokens()
    field = _rule(_INPUTS_CSS, '[data-theme="dark"] .form-control')
    placeholder = _rule(_INPUTS_CSS, '[data-theme="dark"] .form-control::placeholder')
    # Act
    ratio = _contrast(_resolve(placeholder["color"], tokens), _resolve(field["background-color"], tokens))
    # Assert
    assert ratio >= 4.5 and placeholder.get("opacity", "1") == "1", f"placeholder {ratio:.2f}:1"


def test_dark_readonly_form_control_meets_aa():
    # Arrange
    tokens = _dark_tokens()
    rule = _rule(_INPUTS_CSS, '[data-theme="dark"] .form-control[readonly]')
    # Act
    ratio = _contrast(_resolve(rule["color"], tokens), _resolve(rule["background-color"], tokens))
    # Assert
    assert ratio >= 4.5 and rule.get("opacity", "1") == "1", f"readonly {ratio:.2f}:1"


def test_dark_form_select_text_meets_aa():
    # Arrange
    tokens = _dark_tokens()
    rule = _rule(_SELECT_CSS, '[data-theme="dark"] .form-select')
    # Act
    ratio = _contrast(_resolve(rule["color"], tokens), _resolve(rule["background-color"], tokens))
    # Assert
    assert ratio >= 4.5, f"dark .form-select text contrast {ratio:.2f}:1"
