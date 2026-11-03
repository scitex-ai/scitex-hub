"""Owning-shell readiness using the shipped SDK header JavaScript."""

from importlib.util import find_spec
from pathlib import Path

import pytest

from tests.e2e.playwright.page_ready import APP_READY_JS


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("global", True),
        ("sdk", True),
        ("missing_js", False),
        ("empty", False),
        ("nested", False),
    ],
)
def test_readiness_requires_the_owning_shell_renderer(browser, kind, expected):
    # Arrange -- SDK bytes come from the actual installed public dependency.
    sdk = Path(find_spec("scitex_sdk").origin).parent
    header_js = (sdk / "ui/static/scitex_sdk/ui/js/app/app-header.js").read_text()
    context = browser.new_context()
    try:
        page = context.new_page()
        module = '<main class="ws-module-pane"><div data-stx-app-header data-app-title="Owned readiness fixture"></div>'
        module += "" if kind == "empty" else "<p>Owned application content</p>"
        module += "</main>"
        shell = '<div id="workspace-three-col">' + module + "</div>"
        if kind == "nested":
            shell = "<section>" + shell + "</section>"
        page.set_content(
            '<body class="'
            + ("app-ready" if kind == "global" else "")
            + '">'
            + shell
            + "</body>"
        )
        if kind != "missing_js":
            page.add_script_tag(type="module", content=header_js)
            page.locator("[data-stx-app-header-mounted]").wait_for(state="attached")
        # Act -- no fixture sets or simulates the SDK mounted attribute.
        ready = page.evaluate(APP_READY_JS)
        # Assert -- empty/missing-JS/nested shells fail, global lifecycle stays valid.
        assert ready is expected
    finally:
        context.close()
