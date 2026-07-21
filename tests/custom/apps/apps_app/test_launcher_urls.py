#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URL-correctness tests for launcher tiles + dock (nav-404 batch).

Every tile the launcher renders must point at a URL that actually
resolves — the operator field-tested production and found tiles
navigating to the wrong app (Console → Writer) or to 404s (Chat/comms,
pip-installed user apps). These tests pin the fixed wiring.

All tests use the real Django test client against the real ORM — no
mocks (same conventions as test_launcher.py).
"""

from django.contrib.auth.models import User
from django.test import TestCase

from apps.infra.workspace_app.registry import get_all_modules


class LauncherTileUrlTest(TestCase):
    """Launcher tiles must navigate to their own app, never a 404."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="tile-url-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def setUp(self):
        self.client.login(
            username="tile-url-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def _tile(self, name):
        resp = self.client.get("/")
        return next(t for t in resp.context["tiles"] if t["name"] == name)

    def test_console_tile_url_is_console_route(self):
        # Arrange
        module_name = "console"
        # Act
        tile = self._tile(module_name)
        # Assert
        assert tile["launch_url"] == "/apps/console/"

    def test_console_index_does_not_redirect_to_writer(self):
        # Arrange
        url = "/apps/console/"
        # Act
        resp = self.client.get(url)
        # Assert — used to be a 302 to /writer/ (nav-404 batch #1)
        assert resp.status_code == 200

    def test_console_index_renders_console_module_shell(self):
        # Arrange
        url = "/apps/console/"
        # Act
        resp = self.client.get(url)
        # Assert
        assert b'data-active-module="console"' in resp.content

    def test_discovery_index_renders_discovery_module_shell(self):
        # Arrange
        url = "/apps/discovery/"
        # Act
        resp = self.client.get(url)
        # Assert — the shell must declare discovery as the module to
        # load (nav-404 batch #2: shell fell back to "home")
        assert b'data-active-module="discovery"' in resp.content

    def test_comms_index_still_resolves(self):
        # Arrange — the launcher "Chat" tile was dropped (launcher pass 2,
        # redundant with the sidebar /chat/), but the /apps/comms/ route
        # is still reachable from the module tab bar + direct nav, so it
        # must keep resolving (nav-404 batch #3 wired the workspace shell).
        url = "/apps/comms/"
        # Act
        resp = self.client.get(url)
        # Assert
        assert resp.status_code == 200

    def test_every_registry_tile_url_resolves(self):
        # Arrange
        resp = self.client.get("/")
        registry_names = {m.name for m in get_all_modules()}
        tiles = [t for t in resp.context["tiles"] if t["name"] in registry_names]
        # Act — follow redirects: some module URLs legitimately
        # redirect, but never to a 404
        broken = [
            (t["name"], t["launch_url"])
            for t in tiles
            if self.client.get(t["launch_url"], follow=True).status_code == 404
        ]
        # Assert
        assert broken == []

    def test_dock_chat_link_is_chat_pane_route(self):
        # Arrange
        url = "/"
        # Act
        resp = self.client.get(url)
        # Assert — the mobile dock Chat entry targets the chat pane
        assert b'href="/chat/" class="launcher-dock-item"' in resp.content


class UserAppModuleUrlTest(TestCase):
    """User-published apps registered by app_loader must get a routed URL."""

    def _load_user_app(self):
        from apps.workspace.apps_app.models import AppsModule
        from apps.workspace.apps_app.services.app_loader import load_single_app

        app_module = AppsModule.objects.create(
            module_name="t-user-app",
            category="utility",
            visibility="public",
        )
        load_single_app(app_module)

    def _unload_user_app(self):
        from apps.infra.workspace_app.registry import _registry, _registry_by_name

        _registry_by_name.pop("t-user-app", None)
        _registry[:] = [m for m in _registry if m.name != "t-user-app"]

    def test_load_single_app_registers_workspace_shell_url(self):
        # Arrange
        from apps.infra.workspace_app.registry import get_module

        self._load_user_app()
        try:
            # Act
            mod = get_module("t-user-app")
            # Assert — /apps/t-user-app/ is NOT a mounted route; the
            # workspace shell is (nav-404 batch #5)
            assert mod is not None and mod.get_url() == "/apps/workspace/t-user-app/"
        finally:
            self._unload_user_app()


class ToolsUrlTest(TestCase):
    """Tools sidebar links must target routed /apps/tools/ URLs."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="tools-url-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def setUp(self):
        self.client.login(
            username="tools-url-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    @staticmethod
    def _tool_urls():
        from apps.workspace.tools_app.views.tools_data import get_tool_domains

        return sorted(
            {
                tool["bookmarklet_url"]
                for domain in get_tool_domains()
                for tool in domain["tools"]
            }
        )

    def test_every_tool_url_is_under_apps_tools(self):
        # Arrange
        urls = self._tool_urls()
        # Act — the sidebar/iframe URLs used to be /tools/<slug>/,
        # which is unrouted (nav-404 batch #4)
        outside = [u for u in urls if not u.startswith("/apps/tools/")]
        # Assert
        assert outside == []

    def test_every_tool_url_resolves(self):
        # Arrange
        urls = self._tool_urls()
        # Act
        broken = [u for u in urls if self.client.get(u).status_code != 200]
        # Assert
        assert broken == []


# EOF
