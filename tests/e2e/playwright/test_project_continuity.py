#!/usr/bin/env python3
"""Executable login-to-project continuity journey owned by Hub.

CI provisions a registered test account, a private project, and real on-disk app
workspaces before the server starts. The existing authenticated Playwright
fixtures perform the real login; this test crosses the real launcher/app routes.
Stats is the truthful unmounted gap: its coming-soon tile must not invent a URL.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import pytest

from tests.e2e.playwright.page_ready import wait_for_page_ready

pytestmark = pytest.mark.e2e

USERNAME = "test-user"
PROJECT_SLUG = "continuity-paper"
PROJECT_KEY = f"{USERNAME}/{PROJECT_SLUG}"
PROJECT_APPS = ("scholar", "figrecipe", "writer")


@dataclass
class BrowserEvidence:
    console_errors: list[str]
    page_errors: list[str]
    network_failures: list[str]

    def assert_clean(self) -> None:
        assert not self.console_errors, f"browser console errors: {self.console_errors}"
        assert not self.page_errors, f"browser page errors: {self.page_errors}"
        assert (
            not self.network_failures
        ), f"same-origin network failures: {self.network_failures}"


@pytest.fixture(params=["desktop", "mobile"])
def continuity_browser(request, pw_base_url):
    """Existing desktop/390px login fixtures plus console/network evidence."""
    viewport = request.param
    fixture_name = (
        "authenticated_desktop_page"
        if viewport == "desktop"
        else "authenticated_mobile_page"
    )
    page = request.getfixturevalue(fixture_name)
    evidence = BrowserEvidence([], [], [])

    page.on(
        "console",
        lambda message: (
            evidence.console_errors.append(message.text)
            if message.type == "error"
            else None
        ),
    )
    page.on("pageerror", lambda error: evidence.page_errors.append(str(error)))
    page.on(
        "requestfailed",
        lambda failed: (
            evidence.network_failures.append(
                f"{failed.method} {failed.url}: {failed.failure}"
            )
            if failed.url.startswith(pw_base_url)
            else None
        ),
    )
    page.on(
        "response",
        lambda response: (
            evidence.network_failures.append(
                f"{response.status} {response.request.method} {response.url}"
            )
            if response.url.startswith(pw_base_url) and response.status >= 500
            else None
        ),
    )

    return viewport, page, evidence


def _assert_project_metadata(page, app: str, version: str) -> None:
    body = page.locator("body")
    assert body.get_attribute("data-active-project-key") == PROJECT_KEY
    assert body.get_attribute("data-active-app-version") == version
    assert page.locator('meta[name="stx-project-provider"]').count() == 1
    assert page.locator('meta[name="stx-project-provider"]').get_attribute(
        "content"
    ) == ("/api/project/scope/")
    assert page.locator("[data-stx-project-picker]").count() <= 1
    assert page.locator("[id$='app-header']").count() <= 1
    assert urlparse(page.url).path == f"/apps/{app}/"
    assert parse_qs(urlparse(page.url).query)["project"] == [PROJECT_KEY]


def test_login_launcher_and_project_apps_keep_one_project(continuity_browser):
    """Login fixture → launcher → mounted apps → launcher keeps one project."""
    viewport, page, evidence = continuity_browser

    launcher = page.goto("/apps/", wait_until="domcontentloaded")
    assert launcher is not None and launcher.status == 200
    wait_for_page_ready(page)
    assert page.locator("body").get_attribute("data-session-role") == "user"
    assert page.locator("#app-launcher").get_attribute("data-active-project-key") == (
        PROJECT_KEY
    )
    assert page.locator(".launcher-active-project").is_visible()

    stats = page.locator('[data-module="stats"], [data-planned="stats"]')
    assert stats.count() == 1
    stats_href = stats.get_attribute("href")
    apps_to_visit = ["scholar"]
    if stats_href is None:
        assert stats.get_attribute("data-availability") == "coming_soon"
        assert stats.get_attribute("aria-haspopup") == "dialog"
    else:
        stats_path = urlparse(stats_href).path
        if stats_path == "/apps/stats/":
            assert stats.get_attribute("data-scope") == "project"
            assert parse_qs(urlparse(stats_href).query)["project"] == [PROJECT_KEY]
        else:
            # A catalog-only tile may link to its real Store detail page, but
            # must never invent an absent leaf route.
            assert stats_path == "/apps/store/stats/"
            stats_response = page.goto(stats_href, wait_until="domcontentloaded")
            assert stats_response is not None and stats_response.status == 200
            wait_for_page_ready(page)
            page.goto("/apps/", wait_until="domcontentloaded")
            wait_for_page_ready(page)
    apps_to_visit.extend(app for app in PROJECT_APPS if app != "scholar")

    for app in apps_to_visit:
        tile = page.locator(
            f'#launcher-grid [data-module="{app}"]:not([data-favorite-alias])'
        )
        assert tile.count() == 1
        assert tile.get_attribute("data-scope") == "project"
        version = tile.get_attribute("data-version")
        assert version, f"{app} launcher tile did not expose its installed version"
        href = tile.get_attribute("href")
        assert href and parse_qs(urlparse(href).query)["project"] == [PROJECT_KEY]

        response = page.goto(href, wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        wait_for_page_ready(page)
        _assert_project_metadata(page, app, version)

        returned = page.goto("/apps/", wait_until="domcontentloaded")
        assert returned is not None and returned.status == 200
        wait_for_page_ready(page)
        assert (
            page.locator("#app-launcher").get_attribute("data-active-project-key")
            == PROJECT_KEY
        )

    evidence.assert_clean()
    assert viewport in {"desktop", "mobile"}


@pytest.mark.xfail(
    strict=True,
    reason=(
        "scitex-stats mounts /apps/stats/ but does not yet render the Hub host "
        "project/version/provider metadata; mobile navigation also stalls"
    ),
)
def test_stats_leaf_adopts_the_hub_project_contract(authenticated_desktop_page):
    """Executable leaf gap: remove xfail when Stats adopts the host contract."""
    page = authenticated_desktop_page
    page.goto("/apps/", wait_until="domcontentloaded")
    wait_for_page_ready(page)
    stats = page.locator('#launcher-grid [data-module="stats"]')
    if stats.count() == 0:
        pytest.xfail("Stats leaf route is not mounted in this environment")
    href = stats.get_attribute("href")
    assert href and urlparse(href).path == "/apps/stats/"
    response = page.goto(href, wait_until="domcontentloaded")
    assert response is not None and response.status == 200
    assert page.locator("body").get_attribute("data-active-project-key") == PROJECT_KEY
    assert page.locator('meta[name="stx-project-provider"]').count() == 1
