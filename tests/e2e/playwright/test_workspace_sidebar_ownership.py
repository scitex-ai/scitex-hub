"""Real Chromium checks that host utility sizing never captures leaf Details."""

import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


@pytest.mark.parametrize("width", [390, 1440])
@pytest.mark.parametrize("collapsed", [False, True])
def test_host_sidebar_rules_preserve_nested_module_geometry(width, collapsed):
    root = Path(__file__).resolve().parents[3]
    styles = "\n".join(
        (root / rel).read_text()
        for rel in (
            "static/shared/css/components/workspace-layout.css",
            "static/workspace_app/css/workspace-shell.css",
        )
    )
    state = " collapsed" if collapsed else ""
    html = f"""<style>
    *{{box-sizing:border-box}}body{{margin:0}}.workspace-pane{{height:600px}}
    .stx-shell-sidebar{{width:300px;min-width:48px;flex-shrink:0}}
    .stx-shell-sidebar.collapsed{{width:48px!important}}
    .leaf-row{{display:flex;width:100%}}.leaf-main{{flex:1;min-width:0}}
    {styles}</style>
    <div class="workspace-pane active" data-pane="module"><div class="leaf-row">
    <main class="leaf-main">Owned fixture board</main>
    <aside id="leaf" class="stx-shell-sidebar{state}"><button class="panel-toggle-btn">Toggle Details</button></aside>
    </div></div>
    <div class="workspace-pane active" data-pane="editor"><div class="ws-viewer-pane">
    <aside id="utility" class="stx-shell-sidebar collapsed" aria-hidden="true"><div class="stx-shell-sidebar__header"><button class="panel-toggle-btn">Host toggle</button><span class="stx-shell-sidebar__title">Old title</span><span class="stx-shell-sidebar__title-full">Full title</span></div><div class="stx-shell-sidebar__content">Owned content</div></aside>
    </div></div>"""
    with sync_playwright() as runtime:
        executable = os.environ.get(
            "SCITEX_HUB_TEST_CHROMIUM", runtime.chromium.executable_path
        )
        if not Path(executable).is_file():
            pytest.fail(
                "Installed Chromium is required for sidebar geometry regression"
            )
        browser = runtime.chromium.launch(
            executable_path=executable, args=["--no-sandbox"]
        )
        try:
            page = browser.new_page(viewport={"width": width, "height": 844})
            page.set_content(html)
            result = page.evaluate(
                """()=>{const leaf=document.querySelector('#leaf'), utility=document.querySelector('#utility');return {
            leaf:leaf.getBoundingClientRect().width,utility:utility.getBoundingClientRect().width,
            board:document.querySelector('.leaf-main').getBoundingClientRect().width,
            leafToggle:getComputedStyle(leaf.querySelector('button')).display,
            utilityToggle:getComputedStyle(utility.querySelector('button')).display,
            utilityTitle:getComputedStyle(utility.querySelector('.stx-shell-sidebar__title')).display,utilityFullTitle:getComputedStyle(utility.querySelector('.stx-shell-sidebar__title-full')).display,utilityContent:getComputedStyle(utility.querySelector('.stx-shell-sidebar__content')).overflow,utilityDisplay:getComputedStyle(utility).display}}"""
            )
            assert result == {
                "leaf": 48 if collapsed else 300,
                "utility": width,
                "board": width - (48 if collapsed else 300),
                "leafToggle": "inline-block",
                "utilityToggle": "none",
                "utilityTitle": "none",
                "utilityFullTitle": "inline",
                "utilityContent": "auto",
                "utilityDisplay": "flex",
            }
        finally:
            browser.close()
