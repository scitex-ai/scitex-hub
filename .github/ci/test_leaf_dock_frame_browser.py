"""Offline Chromium geometry test for the real Hub leaf-host stylesheet.

The fixture supplies an explicit host frame, not a copied app or dock controller.
It isolates whether the shared CSS inserts layout children at either flex level.
Full app interaction qualification is a separate authenticated browser check.
"""

import os
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def frame_page():
    with playwright.sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.environ.get("SCITEX_TEST_CHROMIUM")
        )
        try:
            page = browser.new_page()
            # No imports, data services or external dependencies are needed to
            # measure this stylesheet's own clearance declarations.
            page.route("**/*", lambda route: route.abort())
            yield page
        finally:
            browser.close()


@pytest.mark.parametrize("width,height,header", [(1440, 900, 65), (390, 844, 45)])
def test_dock_overlay_keeps_both_flex_levels_at_available_height(
    frame_page, width, height, header
):
    # Arrange
    page = frame_page
    page.set_viewport_size({"width": width, "height": height})
    css = (ROOT / "static/shared/css/layouts/leaf-host-chrome.css").read_text()
    page.set_content(f"""
      <style>{css}</style>
      <style>
        html,body {{ margin:0; height:100%; }}
        body {{ display:flex; flex-direction:column; overflow:hidden;
                --site-dock-scroll-clearance:171px; }}
        #fixture-header {{ height:{header}px;flex:none; }}
        .workspace-three-col {{ display:flex; flex-direction:column;
          flex:1; min-height:0; }}
        main {{ display:flex; flex-direction:column; flex:1;
          min-height:0; overflow:auto; }}
        #fixture-app {{ flex:1; min-height:0; }}
        nav.site-dock {{ position:fixed;bottom:10px;left:50%;height:153px;
          width:320px;transform:translateX(-50%); }}
      </style>
      <div id="fixture-header">Host</div>
      <div class="workspace-three-col"><main id="main-content">
        <section id="fixture-app">App</section>
      </main></div>
      <nav class="site-dock">Dock</nav>
    """)
    # Act
    observed = page.evaluate("""() => {
      const ws=document.querySelector('.workspace-three-col');
      const main=document.querySelector('main'),app=document.querySelector('section');
      const dock=document.querySelector('nav');
      return {workspace:ws.clientHeight,main:main.clientHeight,app:app.clientHeight,
        extraScroll:main.scrollHeight-main.clientHeight,
        dockHeight:dock.clientHeight,dockPosition:getComputedStyle(dock).position,
        scrollAlignment:getComputedStyle(main).scrollPaddingBottom};
    }""")
    # Assert
    assert observed == {"workspace": height-header, "main": height-header,
        "app": height-header, "extraScroll": 0, "dockHeight": 153,
        "dockPosition": "fixed", "scrollAlignment": "195px"}
