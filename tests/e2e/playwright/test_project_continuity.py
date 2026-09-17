#!/usr/bin/env python3
"""Executable login-to-project continuity journey owned by Hub.

The test creates its own registered user, project and on-disk workspace, logs in
through the real form, and crosses the real launcher/app routes. Stats is pinned
as the truthful unmounted gap: its coming-soon tile must not invent a URL.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import pytest

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)
from apps.infra.project_app.services.writer_workspace_layout import (
    get_manuscript_path,
)
from tests.e2e.playwright.page_ready import wait_for_page_ready

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

USERNAME = "continuity-user"
PASSWORD = "ContinuityPass123!"  # pragma: allowlist secret
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


@pytest.fixture
def continuity_identity(django_user_model):
    """A registered account with one real project and app workspaces."""
    user = django_user_model.objects.create_user(
        username=USERNAME,
        email="continuity@example.com",
        password=PASSWORD,
    )
    project = Project.objects.create(
        owner=user,
        name="Continuity Paper",
        slug=PROJECT_SLUG,
        description="Cross-app continuity fixture",
        visibility="private",
    )
    manager = get_project_filesystem_manager(user)
    created, project_root = manager.create_project_directory(
        project, use_template=False
    )
    assert created and project_root is not None
    (project_root / "scitex" / "scholar").mkdir(parents=True, exist_ok=True)
    (project_root / "data").mkdir(exist_ok=True)
    get_manuscript_path(project_root).mkdir(parents=True, exist_ok=True)

    user.profile.last_active_repository = project
    user.profile.save(update_fields=["last_active_repository"])

    yield user, project

    shutil.rmtree(manager.base_path.parent, ignore_errors=True)


@pytest.fixture(params=[("desktop", 1440, 900), ("mobile", 390, 844)])
def continuity_browser(browser, static_live_server, settings, request):
    """Desktop and 390px contexts with console/network evidence capture."""
    name, width, height = request.param
    settings.VITE_USE_BUILD = True
    context = browser.new_context(
        base_url=static_live_server.url,
        viewport={"width": width, "height": height},
        ignore_https_errors=True,
    )
    page = context.new_page()
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
            if failed.url.startswith(static_live_server.url)
            else None
        ),
    )
    page.on(
        "response",
        lambda response: (
            evidence.network_failures.append(
                f"{response.status} {response.request.method} {response.url}"
            )
            if response.url.startswith(static_live_server.url)
            and response.status >= 500
            else None
        ),
    )

    yield name, page, evidence

    page.close()
    context.close()


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


def test_login_launcher_and_project_apps_keep_one_project(
    continuity_browser, continuity_identity
):
    """Login → launcher → three mounted apps → launcher keeps one project."""
    viewport, page, evidence = continuity_browser

    login = page.goto("/auth/login/", wait_until="domcontentloaded")
    assert login is not None and login.status == 200
    page.fill('#login-form input[name="username"]', USERNAME)
    page.fill('#login-form input[name="password"]', PASSWORD)
    page.click('#login-form button[type="submit"]')
    page.wait_for_url(lambda url: "/auth/login" not in url)
    wait_for_page_ready(page)

    launcher = page.goto("/apps/", wait_until="domcontentloaded")
    assert launcher is not None and launcher.status == 200
    wait_for_page_ready(page)
    assert page.locator("body").get_attribute("data-session-role") == "user"
    assert page.locator("#app-launcher").get_attribute("data-active-project-key") == (
        PROJECT_KEY
    )
    assert page.locator(".launcher-active-project").is_visible()

    stats = page.locator('[data-module="stats"]')
    assert stats.get_attribute("data-availability") == "coming_soon"
    assert stats.get_attribute("href") is None
    assert stats.get_attribute("aria-disabled") == "true"

    for app in PROJECT_APPS:
        tile = page.locator(f'[data-module="{app}"]:not([data-favorite-alias])')
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
