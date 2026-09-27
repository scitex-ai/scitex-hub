"""Scholar pane-header must not collide with the project picker on phones.

WHAT WENT WRONG. On a ~390px viewport the Scholar tab row (Search from DBs /
Library / Citation Graph) and the project picker shared one 50px flex row
(``.scholar-main .pane-header`` is ``display: flex`` with no wrap), so the tabs
and the ``<select>`` overlapped. The mobile override set ``height: auto`` but
never changed the row direction, leaving both children side by side.

THE FIX (layout only, mobile only). Inside the ``max-width: 768px`` block the
header stacks vertically — tabs row on top, project picker row below — while
the desktop single-row flex layout is untouched. No selector logic is forked:
the project picker markup/JS keeps the SDK SSOT contract, this only re-flows it.
"""

import re
from pathlib import Path

APP = Path(__file__).resolve().parents[4] / "apps" / "workspace" / "scholar_app"
SHEET_08 = APP / "static/scholar_app/css/common/08-scholar-controls.css"
SHELL_07 = APP / "static/scholar_app/css/common/07-stx-shell-layout.css"


def _media_blocks(css, query):
    # Arrange: locate each "@media <query> {" and brace-match its body.
    blocks = []
    for match in re.finditer(r"@media\s*\(" + re.escape(query) + r"\)\s*\{", css):
        depth = 1
        pos = match.end()
        while depth and pos < len(css):
            if css[pos] == "{":
                depth += 1
            elif css[pos] == "}":
                depth -= 1
            pos += 1
        blocks.append(css[match.end() : pos - 1])
    return blocks


def _norm(text):
    # Act helper: ignore whitespace differences in declarations.
    return re.sub(r"\s+", "", text)


def test_mobile_pane_header_stacks_tabs_above_picker():
    # Arrange: the mobile overrides of the shared Scholar control sheet.
    css = SHEET_08.read_text()
    mobile = "\n".join(_media_blocks(css, "max-width: 768px"))
    # Act
    header_rules = re.findall(
        r"\.scholar-main\s+\.pane-header\s*\{([^}]*)\}", mobile
    )
    # Assert
    assert any("flex-direction:column" in _norm(rule) for rule in header_rules)


def test_mobile_project_picker_select_stretches_full_width():
    # Arrange: the mobile overrides of the shared Scholar control sheet.
    css = SHEET_08.read_text()
    mobile = "\n".join(_media_blocks(css, "max-width: 768px"))
    # Act
    picker_rules = re.findall(
        r"\.scholar-project-picker\s+\.form-select\s*\{([^}]*)\}", mobile
    )
    # Assert
    assert any("max-width:none" in _norm(rule) for rule in picker_rules)


def test_desktop_pane_header_stays_single_row():
    # Arrange: the base (non-media) shell rule owns the desktop layout.
    css = SHELL_07.read_text()
    head = css.split("@media")[0]
    # Act
    base_match = re.search(
        r"\.scholar-main\s+\.pane-header\s*\{([^}]*)\}", head
    )
    base_rule = base_match.group(1) if base_match else ""
    # Assert
    assert base_match and "flex-direction" not in _norm(base_rule)
