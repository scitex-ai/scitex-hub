"""A real menu click changes theme once on both Cards panes."""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("path", ["/apps/cards/#dm", "/apps/cards/#board", "/apps/cards/dm#board"])
def test_cards_header_theme_switch(authenticated_desktop_page, path):
    page = authenticated_desktop_page
    with page.expect_response(lambda r: "/auth/api/get-theme/" in r.url) as loaded:
        page.goto(path)
    loaded.value.finished()
    page.wait_for_function("!!window.SciTeX?.theme")
    initial = page.locator("html").get_attribute("data-theme")
    target = "light" if initial == "dark" else "dark"
    toggle = page.locator("#theme-toggle")
    page.locator("#mobile-hamburger-btn").click()
    page.evaluate("""() => {
      window.__themeChanges = [];
      new MutationObserver(() => window.__themeChanges.push(
        document.documentElement.dataset.theme
      )).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
    }""")
    try:
        with page.expect_response(lambda r: "/auth/api/save-theme/" in r.url) as saved:
            toggle.click()
        assert saved.value.ok
        page.wait_for_function("t => document.documentElement.dataset.theme === t", arg=target)
        page.wait_for_timeout(500)
        assert page.evaluate("window.__themeChanges") == [target]
        assert toggle.count() == 1
        assert toggle.inner_text().strip() == toggle.get_attribute(f"data-label-{initial}")
    finally:
        if page.locator("html").get_attribute("data-theme") != initial:
            with page.expect_response(lambda r: "/auth/api/save-theme/" in r.url):
                toggle.click()
